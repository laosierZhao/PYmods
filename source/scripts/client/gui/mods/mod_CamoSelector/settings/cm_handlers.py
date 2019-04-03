from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import CustomizationItemCMHandler as WGCMHandler
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.shared.gui_items import GUI_ITEM_TYPE
from .. import g_config
from ..constants import SelectionMode


class Options(object):
    MODE_GROUP = 'selectionMode_group'
    MODE_OFF = 'selectionMode_off'
    MODE_RANDOM = 'selectionMode_random'
    MODE_TEAM = 'selectionMode_team'
    MODE_CHANGE = 'selectionMode_change'
    SEASON_GROUP = 'season_group'
    SEASON_SUMMER = 'season_summer'
    SEASON_WINTER = 'season_winter'
    SEASON_DESERT = 'season_desert'
    TEAM_GROUP = 'team_group'
    TEAM_ALLY = 'team_ally'
    TEAM_ENEMY = 'team_enemy'
    MODE = (MODE_OFF, MODE_TEAM, MODE_RANDOM)
    SEASON = (SEASON_SUMMER, SEASON_WINTER, SEASON_DESERT)
    TEAM = (TEAM_ALLY, TEAM_ENEMY)
    ALL = MODE + SEASON + TEAM


class CustomizationItemCMHandler(WGCMHandler):
    def _generateOptions(self, ctx=None):
        result = super(CustomizationItemCMHandler, self)._generateOptions(ctx)
        if self.__ctx.isBuy:
            return result
        result = result[-1:]
        item = self.itemsCache.items.getItemByCD(self._intCD)
        if item.itemTypeID != GUI_ITEM_TYPE.CAMOUFLAGE:
            return result
        settings = self.__ctx.getItemSettings(item)
        mode = settings['random_mode']
        getOptionLabel = lambda option: g_config.i18n['contextMenu_' + option]
        getOptionData = lambda option, remove=False, enabled=True: (
            option, getOptionLabel(option + ('_remove' if remove else '')), {'enabled': enabled})
        getSeasonOptionData = lambda option, remove=False, enabled=True: getOptionData(
            option, remove, enabled and (item.priceGroup == 'custom' or item.isHidden))
        getSeasonSubOptionData = lambda option, season: getSeasonOptionData(
            option, season in settings['season'], len(settings['season']) != 1 or season not in settings['season'])
        getTeamOptionData = lambda option, remove=False: getOptionData(option, remove, mode != SelectionMode.OFF)
        sub, modeLabel = [], ''
        for _mode, _option in zip(SelectionMode.ALL, Options.MODE):
            if mode != _mode:
                sub.append(self._makeItem(_option, getOptionLabel(Options.MODE_CHANGE) + getOptionLabel(_option)))
            else:
                modeLabel = getOptionLabel(_option)
        result += (
            self._makeItem(*getSeasonOptionData(Options.SEASON_GROUP), optSubMenu=[
                self._makeItem(*getSeasonSubOptionData(Options.SEASON_SUMMER, SEASONS_CONSTANTS.SUMMER)),
                self._makeItem(*getSeasonSubOptionData(Options.SEASON_WINTER, SEASONS_CONSTANTS.WINTER)),
                self._makeItem(*getSeasonSubOptionData(Options.SEASON_DESERT, SEASONS_CONSTANTS.DESERT))]),
            self._makeItem(Options.MODE_GROUP, getOptionLabel(Options.MODE_GROUP) + modeLabel, optSubMenu=sub),
            self._makeItem(*getTeamOptionData(Options.TEAM_GROUP), optSubMenu=[
                self._makeItem(*getTeamOptionData(Options.TEAM_ALLY, settings['ally'])),
                self._makeItem(*getTeamOptionData(Options.TEAM_ENEMY, settings['enemy']))]))
        return result

    def onOptionSelect(self, optionId):
        if optionId not in Options.ALL:
            return super(CustomizationItemCMHandler, self).onOptionSelect(optionId)
        settings = self.__ctx.getItemSettings(self.itemsCache.items.getItemByCD(self._intCD))
        value = optionId.split('_')[1]
        if optionId in Options.SEASON:
            seasons = settings['season']
            if value not in seasons:
                seasons.append(value)
            else:
                seasons.remove(value)
        elif optionId in Options.MODE:
            settings['random_mode'] = SelectionMode.INDICES[value]
        elif optionId in Options.TEAM:
            settings[value] = not settings[value]
        self.__ctx.onCacheResync()


@overrideMethod(WGCMHandler, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationItemCMHandler, *a, **kw)
