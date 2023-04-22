import dataclasses
import os
from dataclasses import asdict, dataclass, field
from functools import partial
from typing import (Any, Callable, Dict, Iterator, List, Mapping, Optional,
                    Tuple, Union, TypeVar)


PathLike = TypeVar('PathLike', str, os.PathLike)


class GadgetUnboundError(Exception):
    pass


class GadgetAlreadyBoundError(Exception):
    pass


class GadgetBindError(Exception):
    pass


def _dict_factory(pairs: List[Tuple[str, Any]],
                  obj: Any,
                  repr_map: Mapping[str, Callable[[Any],
                                                  Any]]) -> Dict[str, Any]:
    def field_value(obj: Any, field_name: str) -> Any:
        field = next(field for field in dataclasses.fields(obj)
                     if field.name == field_name)
        value = getattr(obj, field.name)
        repr_ = field.metadata.get('repr')
        return (repr_func(value)
                if (value is not None and repr_
                and (repr_func := repr_map.get(repr_)))
                else value)

    def include_field(obj: Any, field_name: str) -> bool:
        field = next(field for field in dataclasses.fields(obj)
                     if field.name == field_name)
        return not field.metadata.get('dict_ommit', False)

    return {name: field_value(obj, name) for name, _ in pairs
            if include_field(obj, name)}


def get_dict_factory(obj: Any) -> Callable[[List[Tuple[str, Any]]],
                                           Dict[str, Any]]:
    repr_map = {
        'hex16': lambda x: f"0x{x:04x}",
        'hex12': lambda x: f"0x{x:03x}",
        'hex8': lambda x: f"0x{x:02x}"
    }
    return partial(_dict_factory, obj=obj, repr_map=repr_map)


@dataclass
class GadgetAttributes:
    bcdUSB: Optional[int]
    bDeviceClass: Optional[int]
    bDeviceSubClass: Optional[int]
    bDeviceProtocol: Optional[int]
    bMaxPacketSize0: Optional[int]
    idVendor: Optional[int]
    idProduct: Optional[int]
    bcdDevice: Optional[int]


@dataclass
class GadgetStrings:
    manufacturer: str
    product: str
    serialnumber: str
    lang: str = field(init=False, repr=False, default='0x409',
                      metadata={'dict_ommit': True}
                      )


@dataclass
class ConfigStrings:
    configuration: str = field(default='')
    lang: str = field(init=False, repr=False, default='0x409',
                      metadata={'dict_ommit': True}
                      )


@dataclass
class ConfigAttributes:
    MaxPower: Optional[int]


class GadgetFunction:
    def __init__(self, name: str, instance_name: str,
                 attrs: Any = None) -> None:
        self.name = name
        self.instance_name = instance_name
        self.attrs = attrs

    @property
    def fullname(self):
        return f'{self.name}.{self.instance_name}'


class GadgetConfig:
    def __init__(self, name: str, number: int,
                 attrs: Any = None, strs: Any = None) -> None:
        self.name = name
        self.number = number
        self.strs = strs
        self.attrs = attrs
        self.functions: List[GadgetFunction] = []

    @property
    def fullname(self):
        return f'{self.name}.{self.number}'

    def bind_fuction(self, func: GadgetFunction) -> None:
        self.functions.append(func)


class GadgetSpace:
    GADGET_DIR = 'usb_gadget'
    STRINGS_DIR = 'strings'
    CONFIGS_DIR = 'configs'
    FUNCTIONS_DIR = 'functions'

    def __init__(self, configfs_path='/sys/kernel/config',
                 udc_path='/sys/class/udc') -> None:
        self.gadget_path = os.path.join(configfs_path, GadgetSpace.GADGET_DIR)
        self.udc_path = udc_path

    def _get_content(self, filepath: PathLike) -> str:
        with open(filepath, 'r') as file:
            content = file.read()
        return content

    def _write_text(self, filename: PathLike, content: Any):
        with open(filename, 'w') as attr_file:
            attr_file.write(f'{content}\n')

    def _write_binary(self, filename: PathLike, content: Union[bytes, bytearray]):
        with open(filename, 'wb') as attr_file:
            attr_file.write(content)

    def bound_udcs(self) -> List[str]:
        root, dirnames, _ = next(os.walk(self.gadget_path))
        return [self._get_content(os.path.join(root, dirname, 'UDC'))
                for dirname in dirnames 
                if os.path.exists(os.path.join(root, dirname, 'UDC'))]

    def udcs(self, unbound_only: bool = True) -> Iterator[str]:
        bound_udcs = self.bound_udcs() if unbound_only else []
        for _, dirnames, files in os.walk(self.udc_path):
            for udc in dirnames+files:
                if udc not in bound_udcs:
                    yield udc

    def store_attrs(self, target_dir: PathLike, attrs_dict):
        os.chdir(target_dir)
        for filename, content in attrs_dict.items():
            print(f'Writing {content} to {filename}')
            if isinstance(content, (bytearray, bytes)):
                self._write_binary(filename, content)
            else:
                self._write_text(filename, content)

    def store_from_dataclass(self, target_dir: PathLike,
                             attrs: Any):
        attrs_dict = asdict(attrs, dict_factory=get_dict_factory(attrs))
        self.store_attrs(target_dir, attrs_dict)

    def add_config(self, gadget: 'USBGadget',
                   config: GadgetConfig,
                   force: bool = False) -> None:
        config_path = os.path.join(self.gadget_path,
                                   gadget.name,
                                   GadgetSpace.CONFIGS_DIR,
                                   config.fullname)
        print(f'Creating path {config_path}')
        os.makedirs(config_path, exist_ok=force)
        if config.attrs:
            self.store_from_dataclass(config_path, config.attrs)
        if config.strs:
            strs_path = os.path.join(config_path,
                                     GadgetSpace.STRINGS_DIR,
                                     config.strs.lang)
            print(f'Creating path {strs_path}')
            os.makedirs(strs_path, exist_ok=force)
            self.store_from_dataclass(strs_path, config.strs)

    def bind_functions(self, gadget, config, force: bool = False):
        function_dir = os.path.join(self.gadget_path,
                                    gadget.name,
                                    GadgetSpace.FUNCTIONS_DIR)
        config_path = os.path.join(self.gadget_path,
                                   gadget.name,
                                   GadgetSpace.CONFIGS_DIR,
                                   config.fullname)
        for function in config.functions:
            function_path = os.path.join(function_dir,
                                         function.fullname)
            bind_path = os.path.join(config_path, function.fullname)
            if not force or not os.path.exists(bind_path):
                os.symlink(function_path, bind_path)

    def add_function(self, gadget: 'USBGadget',
                     function: GadgetFunction,
                     force: bool = False) -> None:
        function_path = os.path.join(self.gadget_path,
                                     gadget.name,
                                     GadgetSpace.FUNCTIONS_DIR,
                                     function.fullname)
        print(f'Creating path {function_path}')
        os.makedirs(function_path, exist_ok=force)
        if function.attrs:
            self.store_from_dataclass(function_path, function.attrs)

    def add_gadget(self, gadget: 'USBGadget', force: bool = False):
        gadget_dir = os.path.join(self.gadget_path, gadget.name)
        os.makedirs(gadget_dir, exist_ok=force)
        if gadget.attrs:
            self.store_from_dataclass(gadget_dir, gadget.attrs)
        if gadget.strs:
            strings_dir = os.path.join(gadget_dir,
                                       GadgetSpace.STRINGS_DIR,
                                       gadget.strs.lang)
            print(f'Creating path {strings_dir}')
            os.makedirs(strings_dir, exist_ok=force)
            self.store_from_dataclass(strings_dir, gadget.strs)
        for config in gadget.configs:
            self.add_config(gadget, config, force=force)
        for function in gadget.functions:
            self.add_function(gadget, function, force=force)
        for config in gadget.configs:
            self.bind_functions(gadget, config, force=force)
        if gadget.UDC:
            self.store_attrs(gadget_dir, {'UDC': gadget.UDC})

    def bind_udc(self, gadget: 'USBGadget') -> None:
        print(f'binding {gadget.name} to {gadget.UDC}')
        if gadget.UDC:
            gadget_dir = os.path.join(self.gadget_path, gadget.name)
            self.store_attrs(gadget_dir, {'UDC': gadget.UDC})


class USBGadget:
    def __init__(self, name: str,
                 attrs: Optional[GadgetAttributes] = None,
                 strs: Optional[GadgetStrings] = None,
                 configs: Optional[List[GadgetConfig]] = None,
                 functions: Optional[List[GadgetFunction]] = None) -> None:
        self.name = name
        self.space: Optional[GadgetSpace] = None
        self.attrs: Optional[GadgetAttributes] = attrs
        self.strs: Optional[GadgetStrings] = strs
        self.configs: List[GadgetConfig] = configs or []
        self.functions: List[GadgetFunction] = functions or []
        self.UDC: Optional[str] = None

    def add_to_space(self, force: bool = False) -> None:
        if self.space is None:
            msg = f"Gadget {self.name} GadgetSpace not defined."
            raise GadgetUnboundError(msg)
        try:
            self.space.add_gadget(self, force=force)
        except FileExistsError:
            print(f'Gadget {self.name} already exists')

    def bind_to_space(self, space: GadgetSpace, force: bool = False) -> None:
        if not force and self.space is not None:
            raise GadgetAlreadyBoundError
        self.space = space

    def enable(self, udc: Optional[str] = None) -> None:
        if self.space is None:
            raise GadgetUnboundError(f'Gadget {self.name} \
                                     is not bound to GadgetSpace')
        if udc is None:
            try:
                udc = next(self.space.udcs())
            except StopIteration:
                raise GadgetBindError('No UDCs available')
        print(udc)
        self.UDC = udc
        self.space.bind_udc(self)
