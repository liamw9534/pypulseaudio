from __future__ import unicode_literals

from ctypes import c_int, c_char_p, cast, POINTER
from pulseaudio.lib_pulseaudio import *

__version__ = '0.1.0'

state_map = {
    PA_CONTEXT_AUTHORIZING: "authorizing",
    PA_CONTEXT_CONNECTING: "connecting",
    PA_CONTEXT_FAILED: "failed",
    PA_CONTEXT_NOAUTOSPAWN: "no auto spawn",
    PA_CONTEXT_NOFAIL: "no fail",
    PA_CONTEXT_NOFLAGS: "no flags",
    PA_CONTEXT_READY: "ready",
    PA_CONTEXT_SETTING_NAME: "setting name",
    PA_CONTEXT_TERMINATED: "terminated",
    PA_CONTEXT_UNCONNECTED: "unconnected",
}


def callback(cb):
    """
    Decorator for wrapping a callback function and handling return
    value storage and termination of sequenced callbacks
    """ 
    def cb_func(*args):
        self = args[0]
        (value, is_last) = cb(*args)
        if (value is not None):
            self._cb_return[cb.__name__] = self._cb_return.get(cb.__name__, []) + \
                [value]
        if (is_last):
            self._cb_event[cb.__name__] = True
    return cb_func


def wait_callback(cb):
    """
    Decorator for wrapping a function such that its termination
    condition depends on when the callback(s) completed.  The
    decorator must be passed the callback function name, as
    a string, in order to access the correct location for
    the callback return value.  This complements the behaviour
    of the callback decorator.
    """ 
    def cb_decorator(f):
        def cb_func(*args):
            self = args[0]
            if (self.state == PA_CONTEXT_READY):
                self._cb_event[cb] = False
                f(*args)
                while (True):
                    pa_mainloop_iterate(self._main_loop, c_int(1), None)
                    if (self._cb_event[cb]):
                        return self._cb_return.pop(cb)
        return cb_func
    return cb_decorator


def wait_state_change(required_state):
    """
    Decorator for wrapping a function such that its termination
    depends on a pulseaudio state change.  The required_state
    argument is substituted with the actual desired value when
    the decorator is used. 
    """
    def cb_decorator(f):
        def cb_func(*args):
            self = args[0]
            f(*args)
            while (self.state != required_state):
                pa_mainloop_iterate(self._main_loop, c_int(1), None)
        return cb_func
    return cb_decorator


class PulseAudio(object):
    """
    Wrapper around lib_pulseaudio for allowing calls to be made synchronously and
    parameters to be passed back as python types rather than ctype.

    This API enforces all calls with a return value to be returned as a list, even
    if only a single item value is returned.  It is the responsibility of the
    caller to remove return value(s) from the list.

    .. warning:: This wrapper is not thread-safe, overlapped API calls are
        not advised.
    """
    __main_loop = None
    __api = None
    __context = None
    _app_name = None
    _cb_event = {}
    _cb_return = {}
    state = None

    def __init__(self, app_name):
        self._app_name = app_name
        self._state_changed = pa_context_notify_cb_t(self._state_changed_cb)

    @property
    def _main_loop(self):
        if not self.__main_loop:
            self.__main_loop = pa_mainloop_new()
        return self.__main_loop

    @property
    def _api(self):
        if not self.__api:
            self.__api = pa_mainloop_get_api(self._main_loop)
        return self.__api
 
    @property
    def _context(self):
        if not self.__context:
            if not self._app_name:
                raise NameError("No pa_context or app name to create it with "
                                "has been given")
            self.__context = pa_context_new(self._api, self._app_name)
            pa_context_set_state_callback(self._context, self._state_changed, None)
        return self.__context

    @wait_state_change(PA_CONTEXT_READY)
    def connect(self, server=None, flags=0):
        """
        Connect to a pulseaudio server.  The connection operation is considered complete
        only following the state transition to PA_CONTEXT_READY.

        TODO: Connect failures and timeout handling.

        :param server: Refer to
            http://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/ServerStrings/
            for a definition of the server string name.
        :type server: string
        :param flags: Refer to
            http://freedesktop.org/software/pulseaudio/doxygen/def_8h.html#abe3b87f73f6de46609b059e10827863b
        :type flags: pa_context_flags
        """
        if server is not None:
            server = c_char_p(server)
        pa_context_connect(self._context, server, flags, None)

    @wait_state_change(PA_CONTEXT_TERMINATED)
    def disconnect(self):
        """
        Disconnect the current pulseaudio connection context.  The disconnect operation is
        considered complete only following the state transition to PA_CONTEXT_TERMINATED.

        TODO: Disconnect failures and timeout handling.
        """
        pa_context_disconnect(self._context)

    @wait_callback('_context_index_cb')
    def load_module(self, module_name, module_args):
        """
        Load a pulseaudio module.

        :param module_name: a valid module name.  See also:: :meth:`get_module_info_list`
        :type module name: string
        :param module_args: a dictionary that defines the arguments to be passed and their values.
            These must be valid in the context of the module being loaded.  No error checking
            is performed.
        :type module_args: dictionary
        :return: module index number assigned for newly loaded module
        :rtype: a list containing module index integer
        """
        # Convert module args dict to a string of form "arg1=val1 ..."
        args = ' '.join([str(i) + '=' + str(module_args[i])
                         for i in module_args.keys()])
        self._load_module = pa_context_index_cb_t(self._context_index_cb)
        pa_context_load_module(self._context,
                               module_name,
                               args,
                               self._load_module,
                               None)

    @wait_callback('_card_info_cb')
    def get_card_info_list(self):
        """
        Obtain a list of all available card_info entries.  Supported
        fields are:
        - name
        - index
        - profiles each containing profile name, description,
            n_sinks and n_sources

        :return: cards and an associated card profile list per card
        :rtype: list of dict items with one dict per card
        """
        self._get_card_info_list = pa_card_info_cb_t(self._card_info_cb)
        pa_context_get_card_info_list(self._context,
                                      self._get_card_info_list,
                                      None)

    @wait_callback('_card_info_cb')
    def get_card_info_by_index(self, index):
        """
        Obtain card_info entry.  Supported fields are:
        - name
        - index
        - profiles each containing profile name, description,
            n_sinks and n_sources

        :param name: Card index
        :type name: integer
        :return: card info and card profile list
        :rtype: list containing single dict item
        """
        self._get_card_info_by_index = pa_card_info_cb_t(self._card_info_cb)
        pa_context_get_card_info_by_index(self._context,
                                          index,
                                          self._get_card_info_by_index,
                                          None)

    @wait_callback('_card_info_cb')
    def get_card_info_by_name(self, name):
        """
        Obtain card_info entry.  Supported fields are:
        - name
        - index
        - profiles each containing profile name, description,
            n_sinks and n_sources

        :param name: Card name
        :type name: string
        :return: card info and card profile list
        :rtype: list containing single dict item
        """
        self._get_card_info_by_name = pa_card_info_cb_t(self._card_info_cb)
        pa_context_get_card_info_by_name(self._context,
                                         name,
                                         self._get_card_info_by_name,
                                         None)

    @wait_callback('_sink_info_cb')
    def get_sink_info_list(self):
        """
        Obtain a list of all available sinks.  Supported
        fields are:
        - name
        - index
        - description
        - associated card (index)
        - mute boolean
        - latency
        - configured_latency
        - monitor_source
        - monitor_source_name
        - volume levels per channel
        - volume level number of steps
        - state enum

        :return: sink information
        :rtype: list of dict items, with one dict per sink
        """
        self._get_sink_info_list = pa_sink_info_cb_t(self._sink_info_cb)
        pa_context_get_sink_info_list(self._context,
                                      self._get_sink_info_list,
                                      None)

    @wait_callback('_sink_info_cb')
    def get_sink_info_by_index(self, index):
        """
        Obtain sink info by index.  Supported fields are:
        - name
        - index
        - description
        - associated card (index)
        - mute boolean
        - latency
        - configured_latency
        - monitor_source
        - monitor_source_name
        - volume levels per channel
        - volume level number of steps
        - state enum

        :param index: sink index
        :type index: integer
        :return: sink information
        :rtype: list with single dict item
        """
        self._get_sink_info_by_index = pa_sink_info_cb_t(self._sink_info_cb)
        pa_context_get_sink_info_by_index(self._context,
                                          index,
                                          self._get_sink_info_by_index,
                                          None)

    @wait_callback('_sink_info_cb')
    def get_sink_info_by_name(self, name):
        """
        Obtain sink info by name.  Supported fields are:
        - name
        - index
        - description
        - associated card (index)
        - mute boolean
        - latency
        - configured_latency
        - monitor_source
        - monitor_source_name
        - volume levels per channel
        - volume level number of steps
        - state enum

        :param name: sink name
        :type name: string
        :return: sink information
        :rtype: list with single dict item
        """
        self._get_sink_info_by_name = pa_sink_info_cb_t(self._sink_info_cb)
        pa_context_get_sink_info_by_name(self._context,
                                         name,
                                         self._get_sink_info_by_name,
                                         None)

    @wait_callback('_source_info_cb')
    def get_source_info_list(self):
        """
        Obtain a list of all available sources.  Supported
        fields are:
        - name
        - index
        - description
        - associated card (index)
        - mute boolean
        - latency
        - configured_latency
        - monitor_of_sink
        - monitor_of_sink_name
        - state enum

        :return: source information
        :rtype: list of dict items, with one dict per source
        """
        self._get_source_info_list = pa_source_info_cb_t(self._source_info_cb)
        pa_context_get_source_info_list(self._context,
                                        self._get_source_info_list,
                                        None)

    @wait_callback('_source_info_cb')
    def get_source_info_by_index(self, index):
        """
        Obtain source info by index.  Supported fields are:
        - name
        - index
        - description
        - associated card (index)
        - mute boolean
        - latency
        - configured_latency
        - monitor_of_sink
        - monitor_of_sink_name
        - state enum

        :param index: source index
        :type index: integer
        :return: source information
        :rtype: list of single dict item
        """
        self._get_source_info_by_index = pa_source_info_cb_t(self._source_info_cb)
        pa_context_get_source_info_by_index(self._context,
                                            index,
                                            self._get_source_info_by_index,
                                            None)

    @wait_callback('_source_info_cb')
    def get_source_info_by_name(self, name):
        """
        Obtain source info by name.  Supported fields are:
        - name
        - index
        - description
        - associated card (index)
        - mute boolean
        - latency
        - configured_latency
        - monitor_of_sink
        - monitor_of_sink_name
        - state enum

        :param name: source name
        :type name: string
        :return: source information
        :rtype: list of single dict item
        """
        self._get_source_info_by_name = pa_source_info_cb_t(self._source_info_cb)
        pa_context_get_source_info_by_name(self._context,
                                           name,
                                           self._get_source_info_by_name,
                                           None)

    @wait_callback('_module_info_cb')
    def get_module_info_list(self):
        """
        Obtain a list of all available sources.  Supported
        fields are:
        - name
        - index
        - module arguments (as dictionary key/value pairs)

        :return: module information
        :rtype: list of dict items, with one dict per module
        """
        self._get_module_info_list = pa_module_info_cb_t(self._module_info_cb)
        pa_context_get_module_info_list(self._context,
                                        self._get_module_info_list,
                                        None)

    @wait_callback('_module_info_cb')
    def get_module_info(self, index):
        """
        Obtain module info by module index.  Supported fields are:
        - name
        - index
        - module arguments (as dictionary key/value pairs)

        :param index: module index
        :type index: integer
        :return: module information
        :rtype: list of single dict item
        """
        self._get_module_info = pa_module_info_cb_t(self._module_info_cb)
        pa_context_get_module_info(self._context,
                                   index,
                                   self._get_module_info,
                                   None)

    @wait_callback('_context_success_cb')
    def unload_module(self, index):
        """
        Unload a pulseaudio module.

        :param index: a valid module index.
            See also:: :meth:`get_module_info_list` and :meth:`load_module`
        :return: module index number unloaded
        :rtype: a list containing module index integer
        """
        self._unload_module = pa_context_success_cb_t(self._context_success_cb)
        pa_context_unload_module(self._context,
                                 index,
                                 self._unload_module,
                                 None)

    @wait_callback('_context_success_cb')
    def set_card_profile_by_index(self, index):
        """
        Set card profile by profile index.

        :param index: a valid card profile index.
            See also:: :meth:`get_card_info_list`
        :return: card profile index number activated
        :rtype: a list containing card profile index integer
        """
        self._set_card_profile_by_index = pa_context_success_cb_t(self._context_success_cb)
        pa_context_set_card_profile_by_index(self._context,
                                             index,
                                             self._set_card_profile_by_index,
                                             None)

    @wait_callback('_context_success_cb')
    def set_card_profile_by_name(self, name):
        """
        Set card profile by profile index.

        :param index: a valid card profile index.
            See also:: :meth:`get_card_info_list`
        :return: card profile index number activated
        :rtype: a list containing card profile index integer
        """
        self._set_card_profile_by_name = pa_context_success_cb_t(self._context_success_cb)
        pa_context_set_card_profile_by_name(self._context,
                                            name,
                                            self._set_card_profile_by_name,
                                            None)

    def _state_changed_cb(self, context, userdata):
        state = pa_context_get_state(context)
        self.state = state

    @callback
    def _card_info_cb(self, context, card_info, eol, user_data):
        if (eol):
            return (None, True)
        ret = {}
        ret['name'] = card_info.contents.name
        ret['index'] = card_info.contents.index
        profiles = cast(card_info.contents.profiles, POINTER(pa_card_profile_info))
        ret['profiles'] = []
        for i in range(card_info.contents.n_profiles):
            ret['profiles'].append({'name': profiles[i].name,
                                    'desc': profiles[i].description,
                                    'n_sinks': profiles[i].n_sinks,
                                    'n_sources': profiles[i].n_sources
                                    })
        return (ret, False)

    @callback
    def _sink_info_cb(self, context, sink_info, eol, user_data):
        if (eol):
            return (None, True)
        ret = {}
        ret['name'] = sink_info.contents.name
        ret['index'] = sink_info.contents.index
        ret['card'] = sink_info.contents.card
        ret['mute'] = True if sink_info.contents.mute else False
        ret['latency'] = sink_info.contents.latency
        ret['configured_latency'] = sink_info.contents.configured_latency
        ret['monitor_source'] = sink_info.contents.monitor_source
        ret['monitor_source_name'] = sink_info.contents.monitor_source_name
        ret['volume'] = {}
        ret['volume']['channels'] = sink_info.contents.volume.channels
        ret['volume']['values'] = [sink_info.contents.volume.values[i]
                                    for i in range(ret['volume']['channels'])]
        ret['n_volume_steps'] = sink_info.contents.n_volume_steps
        ret['state'] = sink_info.contents.state
        ret['desc'] = sink_info.contents.description
        return (ret, False)

    @callback
    def _source_info_cb(self, context, source_info, eol, user_data):
        if (eol):
            return (None, True)
        ret = {}
        ret['name'] = source_info.contents.name
        ret['index'] = source_info.contents.index
        ret['card'] = source_info.contents.card
        ret['desc'] = source_info.contents.description
        ret['mute'] = True if source_info.contents.mute else False
        ret['latency'] = source_info.contents.latency
        ret['configured_latency'] = source_info.contents.configured_latency
        ret['monitor_of_sink'] = source_info.contents.monitor_of_sink
        ret['monitor_of_sink_name'] = source_info.contents.monitor_of_sink_name
        return (ret, False)

    @callback
    def _module_info_cb(self, context, module_info, eol, user_data):
        if (eol):
            return (None, True)
        ret = {}
        ret['name'] = module_info.contents.name
        ret['index'] = module_info.contents.index
        if (module_info.contents.argument is not None):
            ret['argument'] = {i[0]:i[1] for i in
                          [i.split('=') for i in module_info.contents.argument.split()]}
        else:
            ret['argument'] = None
        return (ret, False)

    @callback
    def _context_index_cb(self, context, index, userdata):
        return (index, True)

    @callback
    def _context_success_cb(self, context, success, userdata):
        return (success, True)
