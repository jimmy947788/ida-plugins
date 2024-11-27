import ida_name
import idaapi
import ida_kernwin

###################
# from: https://github.com/igogo-x86/HexRaysPyTools
class ActionManager(object):
    def __init__(self):
        self.__actions = []

    def register(self, action):
        self.__actions.append(action)
        idaapi.register_action(
            idaapi.action_desc_t(action.name, action.description, action, action.hotkey)
        )

    def initialize(self):
        pass

    def finalize(self):
        for action in self.__actions:
            idaapi.unregister_action(action.name)


action_manager = ActionManager()


class Action(idaapi.action_handler_t):
    """
    Convenience wrapper with name property allowing to be registered in IDA using ActionManager
    """
    description = None
    hotkey = None

    def __init__(self):
        super(Action, self).__init__()

    @property
    def name(self):
        return "FridaIDA:" + type(self).__name__

    def activate(self, ctx):
        # type: (idaapi.action_activation_ctx_t) -> None
        raise NotImplementedError

    def update(self, ctx):
        # type: (idaapi.action_activation_ctx_t) -> None
        raise NotImplementedError


############################################################################
import ida_funcs
import idc
import json
import os

from PyQt5 import QtCore
from PyQt5.Qt import QApplication
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QTextEdit

# [offset] => offset of target function in hex value format.
# [funcname] => function name
# [filename] => input file name of IDA. e.g. xxx.so / xxx.exe

default_template = """

const MODULE_NAME="[filename]";
let isFoudModule = false;
let isHooked = false;

 // @ts-ignore
function print_arg(addr) {
    try {
        var module = Process.findRangeByAddress(addr);
        if (module != null) return "\\n"+hexdump(addr) + "\\n";
        return ptr(addr) + "\\n";
    } catch (e) {
        return addr + "\\n";
    }
}

// @ts-ignore
function hook_native_addr(module, offset, funcName, paramsNum) {
    try {
        const funcPtr = module.base.add(offset);
        console.log("offset:", offset)
        console.log("funcPtr:", funcPtr);
        console.log("funcName:", funcName);
        console.log("paramsNum:", paramsNum);

        Interceptor.attach(funcPtr, {
            onEnter: function (args) {
                this.logs = "";
                this.params = [];
                // @ts-ignore
                this.logs=this.logs.concat("So: " + module.name + "  Method: " + funcName + " offset: " + offset + "\\n");
                for (let i = 0; i < paramsNum; i++) {
                    this.params.push(args[i]);
                    this.logs=this.logs.concat("this.args" + i + " onEnter: " + print_arg(args[i]));
                }
            }, onLeave: function (retval) {
                for (let i = 0; i < paramsNum; i++) {
                    this.logs=this.logs.concat("this.args" + i + " onLeave: " + print_arg(this.params[i]));
                }
                this.logs=this.logs.concat("retval onLeave: " + print_arg(retval) + "\\n");
                console.log(this.logs);
            }
        });
    } catch (e) {
        console.log(e);
    }
}

//hook_dlopen
function hook_dlopen(dlopenPtr) {
    Interceptor.attach(dlopenPtr, {
        onEnter: function (args) {
            if (args[0].isNull()) return

            let moduleFullPath = args[0].readCString()
            console.log('dlopen:', moduleFullPath);
            
            if(moduleFullPath == MODULE_NAME || moduleFullPath.includes(MODULE_NAME) &&
                !isFoudModule){
                isFoudModule = true;
                console.warn("foud targe module:", moduleFullPath);
            }

        },
        onLeave: function (retval) {
            
            console.warn("isFoudModule=" + isFoudModule + " isHooked=" + isHooked);
            if(isFoudModule && !isHooked){
                isHooked = true;

                var m = Process.findModuleByName(MODULE_NAME); 
                console.error("module: " + m.name + ", addr: "+ m.base + ", size: " + m.size + ", path: " + m.path);
                
                // hook native function append here 
                // append new hook...
                hook_native_addr(m, ptr([offset]), "[funcname]", 0x1);
            }
        },
    })
}

// start 
setImmediate(function() {
    let dlopenPtr = Module.findExportByName('libdl.so', 'dlopen')
    console.log('dlopen', dlopenPtr);

    let dlopenExPtr = Module.findExportByName('libdl.so', 'android_dlopen_ext')
    console.log('dlopenExPtr', dlopenExPtr);

    hook_dlopen(dlopenPtr)
    hook_dlopen(dlopenExPtr);
});

"""


class Configuration:
    def __init__(self) -> None:
        self.frida_cmd = """frida -U --attach-name="com.example.app" -l gen.js --no-pause"""
        self.template = default_template
        if os.path.exists("IDAFrida.json"):
            self.load()

    def set_frida_cmd(self, s):
        self.frida_cmd = s
        self.store()

    def set_template(self, s):
        self.template = s
        self.store()

    def reset(self):
        self.__init__()

    def store(self):
        try:
            data = {"frida_cmd": self.frida_cmd, "template": self.template}
            open("IDAFrida.json", "w").write(json.dumps(data))
        except Exception as e:
            print(e)

    def load(self):
        try:
            data = json.loads(open("IDAFrida.json", "r").read())
            self.frida_cmd = data["frida_cmd"]
            self.template = data["template"]
        except Exception as e:
            print(e)


global_config = Configuration()


class ConfigurationUI(QDialog):
    def __init__(self, conf: Configuration) -> None:
        super(ConfigurationUI, self).__init__()
        self.conf = conf
        self.edit_template = QTextEdit()
        self.edit_template.setPlainText(self.conf.template)
        layout = QHBoxLayout()
        layout.addWidget(self.edit_template)
        self.setLayout(layout)

    def closeEvent(self, a0) -> None:
        self.conf.set_template(self.edit_template.toPlainText())
        self.conf.store()
        return super().closeEvent(a0)


class ScriptGenerator:
    def __init__(self, configuration: Configuration) -> None:
        self.conf = configuration
        self.imagebase = idaapi.get_imagebase()

    @staticmethod
    def get_idb_filename():
        return os.path.basename(idaapi.get_input_file_path())

    @staticmethod
    def get_idb_path():
        return os.path.dirname(idaapi.get_input_file_path())

    def get_function_name(self,
                          ea):  # https://hex-rays.com/products/ida/support/ida74_idapython_no_bc695_porting_guide.shtml
        """
        Get the real function name
        """
        # Try to demangle
        function_name = idc.demangle_name(idc.get_func_name(ea), idc.get_inf_attr(idc.INF_SHORT_DN))

        # if function_name:
        #    function_name = function_name.split("(")[0]

        # Function name is not mangled
        if not function_name:
            function_name = idc.get_func_name(ea)

        if not function_name:
            function_name = idc.get_name(ea, ida_name.GN_VISIBLE)

        # If we still have no function name, make one up. Format is - 'UNKN_FNC_4120000'
        if not function_name:
            function_name = "UNKN_FNC_%s" % hex(ea)

        return function_name

    def generate_stub(self, repdata: dict):
        s = self.conf.template
        for key, v in repdata.items():
            s = s.replace("[%s]" % key, v)
        return s

    def generate_for_funcs(self, func_addr_list) -> str:
        stubs = []
        for func_addr in func_addr_list:
            dec_func = idaapi.decompile(func_addr)
            repdata = {
                "filename": self.get_idb_filename(),
                "funcname": self.get_function_name(func_addr),
                "offset": hex(func_addr - self.imagebase),
                "nargs": hex(dec_func.type.get_nargs())
            }
            stubs.append(self.generate_stub(repdata))
        return "\n".join(stubs)

    def generate_for_funcs_to_file(self, func_addr_list, filename) -> bool:
        data = self.generate_for_funcs(func_addr_list)
        try:
            open(filename, "w").write(data)
            print("The generated Frida script has been exported to the file: ", filename)
        except Exception as e:
            print(e)
            return False
        try:
            
            clipboard_data = ""
            for func_addr in func_addr_list:
                dec_func = idaapi.decompile(func_addr)

                filename = self.get_function_name(func_addr)
                funcname =  self.get_function_name(func_addr)
                offset = hex(func_addr - self.imagebase)
                nargs = hex(dec_func.type.get_nargs())
                repdata =f"hook_native_addr(m, {offset}, \"{funcname}\", {nargs});\n"
                clipboard_data += repdata

            QApplication.clipboard().setText(clipboard_data)
            print("The generated Frida script has been copied to the clipboard!")
        except Exception as e:
            print(e)
            return False
        return True


class Frida:
    def __init__(self, conf: Configuration) -> None:
        self.conf = conf


class IDAFridaMenuAction(Action):
    TopDescription = "IDAFrida"

    def __init__(self):
        super(IDAFridaMenuAction, self).__init__()

    def activate(self, ctx) -> None:
        raise NotImplemented

    def update(self, ctx) -> None:
        if ctx.widget_type == idaapi.BWN_FUNCS or ctx.widget_type==idaapi.BWN_PSEUDOCODE or ctx.widget_type==idaapi.BWN_DISASM:
            idaapi.attach_action_to_popup(ctx.widget, None, self.name, self.TopDescription + "/")
            return idaapi.AST_ENABLE_FOR_WIDGET
        return idaapi.AST_DISABLE_FOR_WIDGET


class GenerateFridaHookScript(IDAFridaMenuAction):
    description = "Generate Frida Script"

    def __init__(self):
        super(GenerateFridaHookScript, self).__init__()

    def activate(self, ctx):
        gen = ScriptGenerator(global_config)
        idb_path = os.path.dirname(idaapi.get_input_file_path())
        out_file = os.path.join(idb_path, "IDAhook.js")
        if ctx.widget_type==idaapi.BWN_FUNCS:
            selected = [idaapi.getn_func(idx).start_ea for idx in ctx.chooser_selection] #from "idaapi.getn_func(idx - 1)" to "idaapi.getn_func(idx)"
        else:
            selected=[idaapi.get_func(idaapi.get_screen_ea()).start_ea]
        gen.generate_for_funcs_to_file(selected, out_file)

class RunGeneratedScript(IDAFridaMenuAction):
    description = "Run Generated Script"

    def __init__(self):
        super(RunGeneratedScript, self).__init__()

    def activate(self, ctx):
        print("template")


class ViewFridaTemplate(IDAFridaMenuAction):
    description = "View Frida Template"

    def __init__(self):
        super(ViewFridaTemplate, self).__init__()

    def activate(self, ctx):
        ui = ConfigurationUI(global_config)
        ui.show()
        ui.exec_()


class SetFridaRunCommand(IDAFridaMenuAction):
    description = "Set Frida Command"

    def __init__(self):
        super(SetFridaRunCommand, self).__init__()

    def activate(self, ctx):
        print("template")


action_manager.register(GenerateFridaHookScript())
# action_manager.register(RunGeneratedScript())
action_manager.register(ViewFridaTemplate())
# action_manager.register(SetFridaRunCommand())
