# -*- coding: utf-8 -*-
import BigWorld
import inspect
import random
import re
import threading
import urllib
import urllib2
from PlayerEvents import g_playerEvents
from constants import AUTH_REALM
from functools import partial, update_wrapper

MAX_CHAT_MESSAGE_LENGTH = 220
__all__ = ['pickRandomPart', 'sendMessage', 'sendChatMessage', 'remDups', 'checkKeys', 'refreshCurrentVehicle', 'Analytics',
           'Sound', 'showConfirmDialog', 'showI18nDialog', 'showInfoDialog', 'PYViewTools', 'overrideMethod']


def overrideMethod(obj, prop, getter=None, setter=None, deleter=None):
    """
    :param obj: object, which attribute needs overriding
    :param prop: attribute name (can be not mangled), attribute must be callable
    :param getter: fget function or None
    :param setter: fset function or None
    :param deleter: fdel function or None
    :return function: unmodified getter or, if getter is None and src is not property - acts as decorator"""

    if inspect.isclass(obj) and prop.startswith('__') and prop not in dir(obj) + dir(type(obj)):
        prop = obj.__name__ + prop
        if not prop.startswith('_'):
            prop = '_' + prop
    src = getattr(obj, prop)
    if type(src) is property and (getter or setter or deleter):
        props = []
        for func, fType in ((getter, 'fget'), (setter, 'fset'), (deleter, 'fdel')):
            assert func is None or callable(func), fType + ' is not callable!'
            props.append(partial(func, getattr(src, fType)) if func else getattr(src, fType))
        setattr(obj, prop, property(*props))
        return getter
    elif getter:
        getter_orig = getter
        assert callable(src), 'Source property is not callable!'
        assert callable(getter_orig), 'Handler is not callable!'
        getter_new = lambda *args, **kwargs: getter_orig(src, *args, **kwargs)
        while isinstance(getter, partial):
            getter = getter.func
        try:
            update_wrapper(getter_new, getter)
        except AttributeError:
            pass
        if inspect.isclass(obj):
            if inspect.isfunction(src):
                getter_new = staticmethod(getter_new)
            elif getattr(src, '__self__', None) is not None:
                getter_new = classmethod(getter_new)
        setattr(obj, prop, getter_new)
        return getter_orig
    else:
        return partial(overrideMethod, obj, prop)


def pickRandomPart(variantList, lastRandId, doNext=False):
    if not len(variantList):
        return ['', -1]
    if len(variantList) > 1:
        if doNext:
            newId = lastRandId + 1
            if newId >= len(variantList) or newId < 0:
                newId = 0
        else:
            bLoop = True
            newId = 0
            while bLoop:
                newId = random.randrange(len(variantList))
                bLoop = newId == lastRandId

        return variantList[newId], newId
    return variantList[0], 0


def __splitMsg(msg):
    if len(msg) <= MAX_CHAT_MESSAGE_LENGTH:
        return msg, ''
    strPart = msg[:MAX_CHAT_MESSAGE_LENGTH]
    splitPos = strPart.rfind(' ')
    if splitPos == -1:
        splitPos = MAX_CHAT_MESSAGE_LENGTH
    return msg[:splitPos], msg[splitPos:]


def __sendMessagePart(msg, chanId):
    class ClientChat(object):
        from messenger.m_constants import PROTO_TYPE
        from messenger.proto import proto_getter

        def __init__(self):
            pass

        @proto_getter(PROTO_TYPE.BW_CHAT2)
        def proto(self):
            return None

    msg = msg.encode('utf-8')
    import BattleReplay
    if ClientChat.proto is None or BattleReplay.isPlaying():
        from messenger import MessengerEntry
        MessengerEntry.g_instance.gui.addClientMessage('OFFLINE: %s' % msg, True)
        return
    else:
        if chanId == 0:
            ClientChat.proto.arenaChat.broadcast(msg, 1)
        if chanId == 1:
            ClientChat.proto.arenaChat.broadcast(msg, 0)
        if chanId == 2:
            ClientChat.proto.unitChat.broadcast(msg, 1)


def sendChatMessage(fullMsg, chanId, delay):
    currPart, remains = __splitMsg(fullMsg)
    __sendMessagePart(currPart, chanId)
    if len(remains) == 0:
        return
    BigWorld.callback(delay / 1000.0, partial(sendChatMessage, remains, chanId))


def new_addItem(base, self, item):
    if 'temp_SM' in item._vo['message']['message']:
        item._vo['message']['message'] = item._vo['message']['message'].replace('temp_SM', '')
        item._vo['notify'] = False
        if item._settings:
            item._settings.isNotify = False
        return True
    else:
        return base(self, item)


def new_handleAction(base, self, model, typeID, entityID, actionName):
    from notification.settings import NOTIFICATION_TYPE
    if typeID == NOTIFICATION_TYPE.MESSAGE and re.match('https?://', actionName, re.I):
        BigWorld.wg_openWebBrowser(actionName)
    else:
        base(self, model, typeID, entityID, actionName)


def new_callHandler(base, self, buttonID):
    if len(self._SimpleDialog__buttons) == 3:
        self._SimpleDialog__handler(buttonID)
        self._SimpleDialog__isProcessed = True
    else:
        base(self, buttonID)


def new_Dialog_dispose(base, self):
    if len(self._SimpleDialog__buttons) == 3:
        self._SimpleDialog__isProcessed = True  # don't call the handler upon window destruction, onWindowClose is fine
    return base(self)


class DialogButtons(object):
    def __init__(self):
        self.confirm = None
        self.restart = None


_dialogButtons = DialogButtons()


def showSimpleDialog(header, text, meta, callback):
    from gui import DialogsInterface
    from gui.Scaleform.daapi.view.dialogs import SimpleDialogMeta
    DialogsInterface.showDialog(SimpleDialogMeta(header, text, meta, None), callback)


def showConfirmDialog(header, text, buttons, cb):
    showSimpleDialog(header, text, (_dialogButtons.confirm if len(buttons) == 2 else _dialogButtons.restart)(*buttons), cb)


def showI18nDialog(header, text, key, callback):
    from gui.Scaleform.daapi.view.dialogs import I18nConfirmDialogButtons
    showSimpleDialog(header, text, I18nConfirmDialogButtons(key), callback)


def showInfoDialog(header, text, button, callback):
    from gui.Scaleform.daapi.view.dialogs import InfoDialogButtons
    showSimpleDialog(header, text, InfoDialogButtons(button), callback)


# noinspection PyGlobalUndefined
def PMC_hooks():
    global new_addItem, new_handleAction, new_callHandler, new_Dialog_dispose
    from notification.actions_handlers import NotificationsActionsHandlers
    from notification.NotificationsCollection import NotificationsCollection
    from gui.Scaleform.daapi.view.dialogs.SimpleDialog import SimpleDialog
    new_addItem = overrideMethod(NotificationsCollection, 'addItem', new_addItem)
    new_handleAction = overrideMethod(NotificationsActionsHandlers, 'handleAction', new_handleAction)
    new_callHandler = overrideMethod(SimpleDialog, '_SimpleDialog__callHandler', new_callHandler)
    new_Dialog_dispose = overrideMethod(SimpleDialog, '_dispose', new_Dialog_dispose)

    from gui.Scaleform.daapi.view.dialogs import ConfirmDialogButtons
    from gui.Scaleform.daapi.view.dialogs import DIALOG_BUTTON_ID

    class ConfirmButtons(ConfirmDialogButtons):
        def getLabels(self):
            return ({'id': DIALOG_BUTTON_ID.SUBMIT, 'label': self._submit, 'focused': True},
                    {'id': DIALOG_BUTTON_ID.CLOSE, 'label': self._close, 'focused': False})

    class RestartButtons(ConfirmButtons):
        def __init__(self, submit, shutdown, close):
            self._shutdown = shutdown
            super(RestartButtons, self).__init__(submit, close)

        def getLabels(self):
            return ({'id': DIALOG_BUTTON_ID.SUBMIT, 'label': self._submit, 'focused': True},
                    {'id': 'shutdown', 'label': self._shutdown, 'focused': False},
                    {'id': DIALOG_BUTTON_ID.CLOSE, 'label': self._close, 'focused': False})

    _dialogButtons.confirm = ConfirmButtons
    _dialogButtons.restart = RestartButtons


BigWorld.callback(0.0, PMC_hooks)


def remDups(seq):  # Dave Kirby
    # Order preserving
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def sendMessage(text='', colour='Green', panel='Player'):
    from gui.Scaleform.framework import ViewTypes
    from gui.app_loader import g_appLoader
    """
    panel = 'Player', 'Vehicle', 'VehicleError'
    colour = 'Red', 'Purple', 'Green', 'Gold', 'Yellow', 'Self'
    """
    battle = g_appLoader.getDefBattleApp()
    battle_page = battle.containerManager.getContainer(ViewTypes.VIEW).getView()
    if battle_page is not None:
        getattr(battle_page.components['battle%sMessages' % panel], 'as_show%sMessageS' % colour, None)(None, text)
    else:
        BigWorld.callback(0.5, partial(sendMessage, text, colour, panel))


def checkKeys(keys):
    if not keys:
        return False
    for key in keys:
        if isinstance(key, int) and not BigWorld.isKeyDown(key):
            return False
        if isinstance(key, list) and not any(BigWorld.isKeyDown(x) for x in key):
            return False

    return True


def refreshCurrentVehicle():
    from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
    if g_currentPreviewVehicle._CurrentPreviewVehicle__vehAppearance:
        g_currentPreviewVehicle._CurrentPreviewVehicle__vehAppearance.refreshVehicle(g_currentPreviewVehicle.item)
    else:
        g_currentVehicle.refreshModel()
    from HeroTank import HeroTank
    for entity in HeroTank.allCameraObjects:
        if isinstance(entity, HeroTank):
            entity.recreateVehicle()


class Analytics(object):
    def __init__(self, description, version, ID, confList=None):
        self.mod_description = description
        self.mod_id_analytics = ID
        self.mod_version = version
        self.confList = confList if confList else []
        self.analytics_started = False
        self._thread_analytics = None
        self.user = None
        self.playerName = ''
        self.old_user = None
        self.old_playerName = ''
        self.lang = ''
        self.lastTime = BigWorld.time()
        g_playerEvents.onAccountShowGUI += self.start
        BigWorld.callback(0.0, self.game_fini_hook)

    def template(self, old=False):
        return {
            'v': 1,  # Protocol version
            'tid': '%s' % self.mod_id_analytics,  # Mod Analytics ID ('UA-XXX-Y')
            'cid': '%s' % self.old_user if old else self.user,  # User ID
            'an': '%s' % self.mod_description,  # Mod name
            'av': '%s %s' % (self.mod_description, self.mod_version),  # App version.
            'cd': '%s (Cluster: [%s], lang: [%s])' % (
                self.old_playerName if old else self.playerName, AUTH_REALM, self.lang),  # Readable user name
            'ul': '%s' % self.lang,  # client language
            't': 'event'  # Hit type
        }

    def game_fini_hook(self):
        import game

        def new_fini(old_fini):
            try:
                self.end()
            finally:
                old_fini()

        game.fini = partial(new_fini, game.fini)

    def analytics_start(self):
        from helpers import getClientLanguage
        self.lang = str(getClientLanguage()).upper()
        template = self.template()
        requestsPool = []
        if not self.analytics_started:
            requestsPool.append(dict(template, sc='start', t='screenview'))
            for idx, confName in enumerate(self.confList):
                requestsPool.append(dict(template, ec='config', ea='collect', el=confName.split('.')[0]))
            self.analytics_started = True
            self.old_user = BigWorld.player().databaseID
            self.old_playerName = BigWorld.player().name
        elif BigWorld.time() - self.lastTime >= 1200:
            requestsPool.append(dict(template, ec='session', ea='keep'))
        for params in requestsPool:
            self.lastTime = BigWorld.time()
            urllib2.urlopen(url='https://www.google-analytics.com/collect?', data=urllib.urlencode(params)).read()

    # noinspection PyUnusedLocal
    def start(self, ctx):
        player = BigWorld.player()
        if self.user is not None and self.user != player.databaseID:
            self.old_user = player.databaseID
            self.old_playerName = player.name
            self._thread_analytics = threading.Thread(target=self.end, name=threading._newname('Analytics-%d'))
            self._thread_analytics.start()
        self.user = player.databaseID
        self.playerName = player.name
        self._thread_analytics = threading.Thread(target=self.analytics_start, name=threading._newname('Analytics-%d'))
        self._thread_analytics.start()

    def end(self):
        if self.analytics_started:
            from helpers import getClientLanguage
            self.lang = str(getClientLanguage()).upper()
            urllib2.urlopen(url='https://www.google-analytics.com/collect?',
                            data=urllib.urlencode(dict(self.template(True), sc='end', ec='session', ea='end'))).read()
            self.analytics_started = False


class Sound(object):
    def __init__(self, soundPath):
        import SoundGroups
        self.__sndPath = soundPath
        self.__sndTick = SoundGroups.g_instance.getSound2D(self.__sndPath)
        self.__isPlaying = True
        self.stop()

    @property
    def isPlaying(self):
        return self.__isPlaying

    @property
    def sound(self):
        return self.__sndTick

    def play(self):
        self.stop()
        if self.__sndTick:
            self.__sndTick.play()
        self.__isPlaying = True

    def stop(self):
        if self.__sndTick:
            self.__sndTick.stop()
        self.__isPlaying = False


class PYViewTools:
    @staticmethod
    def objToDict(obj):
        if isinstance(obj, list):
            return [PYViewTools.objToDict(o) for o in obj]
        elif hasattr(obj, 'toDict'):
            return {k: PYViewTools.objToDict(v) for k, v in obj.toDict().iteritems()}
        elif isinstance(obj, dict):  # just in case
            return {k: PYViewTools.objToDict(v) for k, v in obj.iteritems()}
        else:
            return obj

    @staticmethod
    def py_printLog(*args):
        for arg in args:
            print arg
