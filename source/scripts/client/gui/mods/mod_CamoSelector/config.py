# coding=utf-8
import BigWorld
import Keys
import ResMgr
import items.vehicles
import nations
import traceback
from PYmodsCore import PYmodsConfigInterface, checkKeys, loadJson, refreshCurrentVehicle, remDups
from gui import InputHandler
from gui.Scaleform.framework.managers.loaders import ViewLoadParams
from gui.app_loader import g_appLoader
from items.components.c11n_constants import SeasonType
from . import __modID__, __date__
from .shared import getCamoTextureName


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.disable = []
        self.hangarCamoCache = {}
        self.camouflagesCache = {}
        self.camouflages = {}
        self.configFolders = {}
        self.currentOverriders = dict.fromkeys(('Ally', 'Enemy'))
        self.hiddenCamo = []
        self.interCamo = []
        self.origInterCamo = []
        self.changedNations = []
        self.activePreviewCamo = None
        self.backupNationID = None
        self.backup = {'mode': 0, 'camoID': (len(nations.NAMES) + 2) * [0]}
        self.isModAdded = False
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = __modID__
        self.version = '2.0.0 (%s)' % __date__
        self.author = '%s (thx to tratatank, Blither!)' % self.author
        self.defaultKeys = {'selectHotkey': [Keys.KEY_F5, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
                            'selectHotKey': ['KEY_F5', ['KEY_LCONTROL', 'KEY_RCONTROL']]}
        self.data = {'enabled': True, 'doRandom': True, 'useBought': True, 'hangarCamoKind': 0,
                     'fullAlpha': False, 'disableWithDefault': False,
                     'selectHotkey': self.defaultKeys['selectHotkey'], 'selectHotKey': self.defaultKeys['selectHotKey']}
        self.i18n = {
            'UI_description': 'Camouflage selector',
            'UI_flash_tabs_0_text': 'Shop',
            'UI_flash_tabs_0_tooltip': '',
            'UI_flash_tabs_1_text': 'Hidden',
            'UI_flash_tabs_1_tooltip': '',
            'UI_flash_tabs_2_text': 'International',
            'UI_flash_tabs_2_tooltip': '',
            'UI_flash_tabs_3_text': 'Custom',
            'UI_flash_tabs_3_tooltip': '',
            'UI_flash_switcher_setup': 'SETUP',
            'UI_flash_switcher_install': 'INSTALL',
            'UI_flash_commit_apply': 'Apply',
            'UI_flash_commit_install': 'Install',
            'UI_flash_randMode_label': 'Random selection mode',
            'UI_flash_randMode_off': 'Disable',
            'UI_flash_randMode_include': 'Include',
            'UI_flash_randMode_override': 'Override',
            'UI_flash_header': 'Camouflages setup',
            'UI_flash_header_tooltip': ('Advanced settings for camouflages added by CamoSelector by '
                                        '<font color=\'#DD7700\'><b>Polyacov_Yury</b></font>'),
            'UI_flash_camoMode_modded': 'Modded',
            'UI_flash_camoMode_international': 'International',
            'UI_flash_randomOptions_text': 'Random selection mode',
            'UI_flash_randomOptions_tooltip': (
                ' • <b>OFF</b>: camouflage is disabled.\n • <b>Override random selection</b>: this camouflage gets '
                'included into a list of camouflages which appear <b>instead of</b> default ones when a random option is '
                'being selected.\n • <b>Include in random selection</b>: this camouflage is included into a list of '
                'camouflages which may appear <b>along with</b> default ones when a random option is being selected. '
                'Please note that these camouflages get <b>overridden</b> by ones that have an option above selected.'),
            'UI_flash_randomOptions_OFF': 'OFF',
            'UI_flash_randomOptions_overrideRandom': 'Override random selection',
            'UI_flash_randomOptions_includeInRandom': 'Include in random selection',
            'UI_flash_useFor_header_text': 'Use this camouflage for:',
            'UI_flash_useFor_header_tooltip': (
                'This camouflage will be used for these groups of tanks.\n'
                '<b>Attention</b>: a camouflage with no tick set will be considered disabled.'),
            'UI_flash_useFor_ally_text': 'Player and allies',
            'UI_flash_useFor_enemy_text': 'Enemies',
            'UI_flash_season_header_text': 'Camouflage season:',
            'UI_flash_season_header_tooltip': (
                'This camouflage will appear on these map seasons.\n'
                '<b>Attention</b>: a camouflage with no tick set will be considered disabled.'),
            'UI_flash_season_winter_text': 'Winter',
            'UI_flash_season_summer_text': 'Summer',
            'UI_flash_season_desert_text': 'Desert',
            'UI_flash_installTooltip': '{HEADER}Install{/HEADER}{BODY}"Buy" this camouflage for selected tank.{/BODY}',
            'UI_flash_save': 'Save',
            'UI_setting_doRandom_text': 'Select random camouflages',
            'UI_setting_doRandom_tooltip': (
                'If enabled, mod will select a random available camouflage if no other option is provided.'),
            'UI_setting_useBought_text': 'Use bought camouflages in battle',
            'UI_setting_useBought_tooltip': "If enabled, mod will preserve bought camouflages on other players' tanks.",
            'UI_setting_selectHotkey_text': 'Camouflage select hotkey',
            'UI_setting_selectHotkey_tooltip': (
                'This hotkey will permanently install currently selected preview camouflage to current tank.'),
            'UI_setting_disableWithDefault_text': 'Disable for vehicles with default camouflage',
            'UI_setting_disableWithDefault_tooltip': 'If enabled, mod will ignore vehicles with a default camouflage.',
            'UI_setting_fullAlpha_text': 'Non-transparent modded camouflages',
            'UI_setting_fullAlpha_tooltip': 'If enabled, all modded camouflages lose their transparency.\n'
                                            'Some call this "dirt-less skins".',
            'UI_setting_hangarCamoKind_text': 'Hangar camouflage kind',
            'UI_setting_hangarCamoKind_tooltip': 'This setting controls a kind which is used in hangar.',
            'UI_setting_hangarCamo_winter': 'Winter', 'UI_setting_hangarCamo_summer': 'Summer',
            'UI_setting_hangarCamo_desert': 'Desert', 'UI_setting_hangarCamo_random': 'Random',
            'UI_camouflagePreview': '<b>Camouflage Selector:</b>\nCamouflage previewing:\n',
            'UI_camouflagePreviewError': '<b>Camouflage Selector:</b>\nCamouflage not found:\n',
            'UI_camouflageRestore': '<b>Camouflage Selector:</b>\nLoading previous camouflage.',
            'UI_camouflageSave': '<b>Camouflage Selector:</b>\nSaving custom camouflage settings.',
            'UI_camouflageSelect': '<b>Camouflage Selector:</b>\nInstalling selected camouflages.',
            'UI_installCamouflage': ('<b>Camouflage Selector:</b>\nCamouflage installed: <b>{name}</b>, '
                                     'camouflage kind: <b>{kind}</b>'),
            'UI_installCamouflage_already': ('<b>Camouflage Selector:</b>\nCamouflage <b>already</b> installed: '
                                             '<b>{name}</b>, camouflage kind: <b>{kind}</b>'),
            'UI_customOrInvalid': ('<b>Camouflage Selector:</b>\nCustom or invalid camouflage detected for '
                                   '<b>{kind}</b> camouflages: <b>{name}</b>'),
            'UI_customOrInvalid_winter': 'winter', 'UI_customOrInvalid_summer': 'summer',
            'UI_customOrInvalid_desert': 'desert'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [self.tb.createOptions('hangarCamoKind', [self.i18n['UI_setting_hangarCamo_%s' % x] for x in
                                                                     ('winter', 'summer', 'desert', 'random')]),
                            self.tb.createControl('doRandom'),
                            self.tb.createControl('disableWithDefault')],
                'column2': [self.tb.createHotKey('selectHotkey'),
                            self.tb.createEmpty(), self.tb.createEmpty(),
                            self.tb.createControl('useBought'),
                            self.tb.createControl('fullAlpha')]}

    def onMSADestroy(self):
        try:
            from gui.mods import mod_remodenabler
        except ImportError:
            refreshCurrentVehicle()

    def onApplySettings(self, settings):
        super(self.__class__, self).onApplySettings(settings)
        self.hangarCamoCache.clear()
        if self.isModAdded:
            kwargs = dict(id='CamoSelectorUI', enabled=self.data['enabled'])
            try:
                BigWorld.g_modsListApi.updateModification(**kwargs)
            except AttributeError:
                BigWorld.g_modsListApi.updateMod(**kwargs)

    def readCurrentSettings(self, quiet=True):
        super(ConfigInterface, self).readCurrentSettings(quiet)
        if 'modded' in self.camouflages:
            return
        self.configFolders.clear()
        self.camouflages = {'modded': {}}
        self.camouflagesCache = loadJson(self.ID, 'camouflagesCache', self.camouflagesCache, self.configPath)
        try:
            camoDirPath = '../' + self.configPath + 'camouflages'
            camoDirSect = ResMgr.openSection(camoDirPath)
            for camoName in remDups(
                    (x for x in camoDirSect.keys() if ResMgr.isDir(camoDirPath + '/' + x))
                    if camoDirSect is not None else []):
                self.configFolders[camoName] = confFolder = set()
                fileName = self.configPath + 'camouflages/' + camoName + '/'
                settings = loadJson(self.ID, 'settings', {}, fileName)
                if 'kinds' in settings:
                    settings['season'] = settings['kinds']
                    del settings['season']
                for key in settings:
                    confFolder.add(key)
                self.camouflages['modded'].update(settings)
        except StandardError:
            traceback.print_exc()
        camouflages = items.vehicles.g_cache.customization20().camouflages
        camoNames = {id: getCamoTextureName(x) for id, x in camouflages.iteritems() if 'modded' not in x.priceGroupTags}
        camoIndices = {}
        for camoID, camoName in camoNames.iteritems():
            camoIndices.setdefault(camoName, []).append(camoID)
        self.interCamo = []
        for camoName, indices in camoIndices.iteritems():
            nationsList = []
            for ID in indices:
                for filterNode in camouflages[ID].filter.include:
                    if filterNode.nations:
                        nationsList += filterNode.nations
            if set(nationsList) == set(xrange(len(nations.NAMES))):
                self.interCamo.append(camoName)
            elif len(set(nationsList)) > 1:
                print camoName, set(nationsList)
        self.hiddenCamo = [camoID for camoID in camoNames if 'notInShop' in camouflages[camoID].priceGroupTags]
        settings = loadJson(self.ID, 'settings', {}, self.configPath)
        if 'disable' in settings:
            if not settings['disable']:
                del settings['disable']
            else:
                self.disable = settings['disable']
        if 'remap' in settings:
            conf = settings['remap']
            for camoName in conf.keys():
                if camoName not in camoNames.values():
                    print '%s: unknown camouflage for remapping: %s' % (self.ID, camoName)
                    del conf[camoName]
            for camoID, camouflage in camouflages.items():
                camoName = getCamoTextureName(camouflage)
                if camoName not in conf:
                    continue
                camoInShop = camoID not in self.hiddenCamo
                if conf[camoName].get('random_mode') == 2 or conf[camoName].get(
                        'random_mode') == 1 and camoName not in self.interCamo:
                    del conf[camoName]['random_mode']
                seasons = conf[camoName].get('season')
                if seasons is not None:
                    if camoInShop:
                        del conf[camoName]['season']
                        print '%s: in-shop camouflage kind changing is disabled (name: %s, season setting was %s)' % (
                            self.ID, camoName, seasons)
                    else:
                        seasonNames = [x for x in seasons.split(',') if x]
                        seasonType = 0
                        for season in seasonNames:
                            try:
                                seasonType |= getattr(SeasonType, season.upper())
                            except AttributeError:
                                print '%s: unknown season name for camouflage %s: %s' % (self.ID, camoName, season)
                        if seasonType == camouflage.season:
                            del conf[camoName]['season']
                for team in ('Ally', 'Enemy'):
                    if conf[camoName].get('useFor%s' % team):
                        del conf[camoName]['useFor%s' % team]
                if not conf[camoName]:
                    del conf[camoName]
            if not conf:
                del settings['remap']
            else:
                self.camouflages['remap'] = conf
        newSettings = {}
        if self.disable:
            newSettings['disable'] = self.disable
        if 'remap' in settings:
            newSettings['remap'] = settings['remap']
        loadJson(self.ID, 'settings', newSettings, self.configPath, True)

    def registerSettings(self):
        super(self.__class__, self).registerSettings()
        kwargs = dict(
            id='CamoSelectorUI', name=self.i18n['UI_flash_header'], description=self.i18n['UI_flash_header_tooltip'],
            icon='gui/flash/CamoSelector.png', enabled=self.data['enabled'], login=False, lobby=True,
            callback=lambda: g_appLoader.getDefLobbyApp().loadView(ViewLoadParams('CamoSelectorMainView')))
        try:
            BigWorld.g_modsListApi.addModification(**kwargs)
        except AttributeError:
            BigWorld.g_modsListApi.addMod(**kwargs)
        self.isModAdded = True


def lobbyKeyControl(event):
    if event.isKeyDown() and not g_config.isMSAWindowOpen:
        if checkKeys(g_config.data['selectHotkey']):
            pass  # installSelectedCamo()


def inj_hkKeyEvent(event):
    LobbyApp = g_appLoader.getDefLobbyApp()
    try:
        if LobbyApp and g_config.data['enabled']:
            lobbyKeyControl(event)
    except StandardError:
        print 'CamoSelector: ERROR at inj_hkKeyEvent'
        traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent
g_config = ConfigInterface()
# TODO: statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-7', _config.configFolders)
