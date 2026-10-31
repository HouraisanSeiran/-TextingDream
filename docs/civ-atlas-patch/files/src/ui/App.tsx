import { readUrl } from './appLocation';
import './theme.css';
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { createPortal, flushSync } from 'react-dom';
import { DEFAULT_PARAMS, type World, type WorldParams } from '../gen/world';
import type { Raster } from '../gen/raster';
import { dropRealisticBasesExcept, realisticRiverSteps, renderRealistic, takeRealisticPainted } from '../render/realistic';
import { adoptPlan, dropFantasyBasesExcept, renderFantasy } from '../render/fantasy';
import { DETAIL_K } from '../render/detail';
import { TerrainDetail } from './TerrainDetail';
import { MapDecor } from './MapDecor';
import { GratLabels } from './GratLabels';
import type { GratSpec } from './graticuleLabels';
import { ContourLayer } from './ContourLayer';
import { contourInk } from '../render/contours';
import { dropPreparedRivers, nearX, wrapOf } from '../render/common';
import {
  centerX,
  clampCurved,
  clampSphere,
  getMapCenter,
  handleMapCenterRequests,
  lonOfX,
  mirrorCanvas,
  publishMapCenter,
  requestMapCenter,
  stageToWorld,
  useMapCenter,
  viewCentredAt,
  worldToStage,
  windowSpan,
  xOfLon,
  type MapView,
  type StageBox,
} from './mapWrap';
import { projectWorld, projectWorldNear, unprojectRel, unprojectWorld, wrapLon, type MapProj } from '../render/projection';
import {
  GLOBE_READY,
  ProjLayer,
  curvedProj,
  getProjection,
  isCurved,
  isGraticuleStep,
  isMapProjection,
  pageColor,
  presentTerrain,
  terrainRefining,
  setContourKind,
  setGraticule,
  setGraticuleStep,
  setMapMoving,
  setProjection,
  useContourKind,
  useGraticuleLines,
  useMapMoving,
  useProjection,
  type MapProjection,
} from './projection';
import { LAYERS, renderLayer, type LayerId } from '../render/layers';
import { Legend } from './Legend';
import type { EraWorld, TempoNote, WorkerRequest, WorkerResponse } from '../worker';
import type { Civ } from '../gen/civ/types';
import { CivLayer, civOpenSteps } from './CivLayer';
import { CivPartInbox } from '../civParts';
import { CivTimeline } from './CivTimeline';
import { ExtendDock, ExtendPop, ExtendSheet } from './ExtendYears';
import { extendProgress, getExtend, noteExtendSpeed, resetExtend, setExtendBusy, setExtendFresh, setExtendOpen, setExtendRunner } from './extendStore';
import { EventPins, type WorldToClient } from './EventPins';
import { DirectorCaption, DirectorEngine, DirectorPanels, DirectorPin } from './Director';
import { directorHandBack, setDirectorMode, useDirectorFly, useDirectorOn } from './directorStore';
import { StepDock, StepPins, StepReviewSheet, StepTimeline, StepwiseEngine, stepwiseNudge, stepwiseToggle, useStepCard, useStepReplay, useStepStrip } from './Stepwise';
import { SAVE_SUFFIX, StepRewindDialog, StepSaveDialog, StepStartDialog } from './StepwiseDialogs';
import {
  enterStepwise,
  getStepGesture,
  getStepwise,
  leaveStepwise,
  onStepGestureEnd,
  rewoundTo,
  setStepGesture,
  saveBackEdits,
  setStepwiseActions,
  stepLost,
  stepWheel,
  stepwiseActions,
  branchSwitching,
  subscribeStepwise,
  useStepwiseOn,
  useStepwiseStopped,
} from './stepwiseStore';
import { branchList, rewindBranch, startStepwise, switchBranch } from '../gen/stepwise';
import { StepBranchDeleteDialog, branchNote, branchRef } from './StepBranches';
import { HistoryBook } from './HistoryBook';
import { AiSettingsHost } from './AiSettings';
import { AccountHost, ShareGone, SharedHint, closeTrash, openLogin, setGoHome, useTrashView } from './AccountDialogs';
import { openBundleText } from './bundle';
import { serverBase } from '../account/server';
import { getSession, takeInviteFromUrl } from '../account/session';
import { setReloadHandler, startSync } from '../account/sync';
import { SHARE_CODE_RE, openShareCode, shortLink } from '../account/cloud';
import { ServerError } from '../account/server';
import { highlightBox, highlightMarks } from '../render/civ/highlight';
import {
  clearChroniclePick,
  clearSelection,
  getChronicle,
  getCivShow,
  getCivTime,
  useCivStory,
  getSelection,
  pausePlayback,
  prepareCivReplay,
  sameSelection,
  startAutoplay,
  resetCivTime,
  setChronicle,
  setCivTime,
  takeAutoplay,
  setCivShow,
  setSelection,
  setSelectionRedirect,
  startCivReplay,
  stepYear,
  togglePlayback,
  useChronicle,
  useCivHighlight,
  getCivHighlight,
  setCivHighlight,
  useChroniclePick,
  useCivShow,
  useSelection,
  type MapSelection,
} from './civView';
import {
  EMPTY_EDITS,
  END_YEAR_DEFAULT,
  GENERATOR_VERSION,
  applyNames,
  aiNameKeys,
  cleanAdvance,
  cleanCivSeed,
  cleanEndYear,
  cleanPlay,
  extendedEndYear,
  faithKey,
  issueCommands,
  keySeats,
  ownInterventions,
  namesWithoutAi,
  newHistoryEdits,
  placeKeyOf,
  playFromOf,
  polityKey,
  regionKey,
  resolveKey,
  sameInterventions,
  settlementKey,
  treatyKey,
  upgradeLegacyKeys,
  type Intervention,
  type PlayState,
  type Plot,
  type PlotReview,
  type TerrainOp,
  type Upheaval,
  type WorldEdits,
} from '../gen/edits';
import { sameTerrain, sameUpheavals } from '../gen/terrainEdits';
import { multisetDiff } from '../gen/util';
import { sameMix, type NameMix } from '../gen/names/mix';
import { cleanFrontier, cleanOrigins, sameFrontier, sameOrigins, type Frontier, type Origins } from '../gen/civ/frontier';
import { cleanCalamity, type Calamity } from '../gen/civ/calamity';
import type { RasterPatch } from '../gen/rasterPatch';
import { cancelTerrainPatch, patchSourceOf, startTerrainFull, startTerrainPatch, type PatchStats, type PatchView, type PreProjected } from './terrainPatch';
import { baseReady, later, overlayReady, thumbPrepSteps } from './thumbPrep';
import { cancelDetailJob, submitDetailJob, type WorkStep } from './detailJobs';
import { baseRegions, civAtEra, composedOf, dropComposed, eraData, peekEraData, eraIndex, eraMapsOf, eraReady, eraShown, patchKey, reuseRegions, useEraIndex, withHistory, type EraMaps } from './eras';
import { adoptChronicle, dropChronicleParts, namedHistory, takeChroniclePart, useNamedHistory } from './chronicleHandoff';
import { sameSketch, sketchGrid, type SketchEdit } from '../gen/sketch';
import { condList, summarize } from '../gen/finder/query';
import { addMark, askHistory, clearEditHistory, clearEdits, getEdits, putEditsQuiet, putOutlineResult, putPlay, removeEditsBatch, removeIntervention, removeUpheaval, setEditGate, setEdits, setEndYear, setHistoryGate, setOutlinePlots, undoTerrainOp, useEdits } from './editsStore';
import { eraText, spaced, yearAt, yearFull } from '../gen/era';
import { redoLastEdit, undoLastEdit } from './undo';
import { useShortcuts } from './useShortcuts';
import { openJump } from './JumpYear';
import { ShortcutsHost, openShortcuts } from './ShortcutsDialog';
import { DiagHost } from './DiagDialog';
import { TipLayer } from './Tips';
import { openSaveMenu } from './SaveMenu';
import { replayStart } from './timelineLayout';
import {
  checkWarning,
  cleanCamera,
  cleanMoment,
  cleanSignature,
  cleanTitle,
  decodeShare,
  editCount,
  GEN_KEY,
  isContourKind,
  isMomentHash,
  isShareHash,
  momentYearMax,
  parseSave,
  resolveMoment,
  versionNote,
  editedWorld,
  worldCheck,
  worldKey,
  type ParseResult,
  type ResolvedMoment,
  type SaveCamera,
  type SaveFile,
  type SaveMoment,
  type SaveOrigin,
  type SaveView,
} from '../gen/savefile';
import {
  THUMB_H,
  THUMB_W,
  attachWorld,
  briefError,
  briefWarning,
  currentOriginal,
  currentUnsaved,
  currentWorld,
  deleteWorld,
  detachWorld,
  flushThumb,
  importSave,
  isStored,
  isWorldId,
  keepWorld,
  legacyWorld,
  listWorlds,
  loadWorld,
  markCreated,
  markOpened,
  newWorldId,
  nextTitle,
  notify,
  persistent,
  refreshThumb,
  overwriteWorld,
  renameWorld,
  sameOrigin,
  saveAsNewVersion,
  saveCurrentAs,
  saveCurrentAsMap,
  stepOrigin,
  setMapThumbMaker,
  setReopenHandler,
  setThumbEditing,
  setThumbMaker,
  setWorldStats,
  startAutoSave,
  storageFullWhy,
  updateCheck,
  useSavesVersion,
  viewChanged,
  type StoredWorld,
  type WorldKind,
} from './saveStore';
import { getStage, setStage, useStage, type DraftBase, type Stage } from './stageStore';
import { setNewCivHandler, setOpenWorldHandler } from './newCivAction';
import { polityAlive, polityName } from '../gen/civ/growth';
import { CIV_SHOW_OFF, civOverlaySteps, drawCivOverlay, type CivDrawParams } from '../render/civ/overlay';
import { finishPick, getPolityPick, interventionActorThen, interventionDoneText, setPickHover, setPolityPick, usePolityPick } from './Interventions';
import { policyDoneText } from './policyInfo';
import { disasterDoneArea, newIvDoneText } from './newIvInfo';
import { RoleBar } from './RoleBar';
import { Inspector } from './Inspector';
import { TargetLayer } from './TargetPlates';
import { FLY_MS, animProgress, curvedFly, easeOutCubic, flatFly, freeArea, markFocus, personKey, pointsFocus, resolvePersonKey, selectionFocus, selectionKey, shownYearOf, sideRoom, phoneFree, type FlyGoal, type Focus } from './flyTo';
import { setMomentSource, type MomentNow } from './shareMoment';
import { decodePresetHash, isPresetHash, type PresetLinkResult } from './presetLink';
import { MarkLayer, markHitAt, markPinAt, markPinTip, type MarkApi } from './MarkLayer';
import { cancelDraft, getMarkUi, newMarkDraft, patchDraft, resetMarkUi, setMarkDragging, stopPlacing, toggleDraftRegion, useMarkUi } from './markStore';
import { markHover, markSpot, ownerName } from './markInfo';
import { CharacterLayer, characterPinAt, characterPinTip } from './CharacterLayer';
import { draftAsCharacter, escapeCharacter, getCharUi, parseYear as parseCharYear, pickPlace, resetCharacterUi, stopPicking, useCharUi } from './characterStore';
import { characterHover, placeOf, whereOfCity, whereOfRegion } from './characterInfo';
import { applyCharacters, lifeStops, type Where } from '../gen/characters';
import { crownDoneText, crownWho, takeCrownResim, type CrownResimNote } from './crownInfo';
import { regionLabel } from '../gen/civ/display';
import { NAME_ZOOM } from '../render/marks';
import { collapseSide, expandSide, getSide, setSideHold, useSide } from './sideStore';
import { getPanel, setSheet, setWorldSheet, usePanel } from './panelStore';
import { closeOverview, getPeople, openOverview, setPeople, useOverview } from './overviewStore';
import { setOutlineFinder, setOutlineRun, setOutlineRunner } from './outlineStore';
import { moveOutline, outlineFrom, outlineRoles, type OutlineFrom } from './outlineMove';
import { outlineDoneToast, outlineRunToast } from './OutlineSide';
import { OutlineRunAsk } from './OutlineRunAsk';
import { FinderPage } from './FinderPage';
import { FinderOverlay, FinderPins } from './FinderMap';
import { pickedOf, variantOf, type FinderFlyTo, type FinderPreview } from './FinderResults';
import { closeFinder, getFinder, openFinder, resetFinder, selectFinder, setFinderMap, setQuery, useFinder, type FinderBase } from './finderStore';
import { foundDetail, storyPoints } from './finderInfo';
import { foundPickOf, putFound, setFindAgainHandler, type FoundPick } from './foundStore';
import type { StudioFound } from './studio/Studio';
import { carryStudioView, takeStudioView } from './studio/studioStore';
import { STUDIO_STYLES, Studio } from './studio/Studio';
import { setFlatGeomSource, useStudioFlat } from './studio/studioStore';
import { MyWorlds, showMapInWorlds } from './MyWorlds';
import { GalleryPage, WorkGone, workWho } from './Gallery';
import { MapWorkView, WorkBar } from './GalleryWork';
import { fetchWork, galleryHref, galleryOfUrl, isWorkGone, isWorkId, loadGallery, workLink, type GalleryItem, type GalleryWork } from '../account/gallery';
import { mapBriefOf } from './mapGroups';
import { NARROW_MAX, isNarrow, useCoarse, useNarrow } from './device';
import { isDoubleTap, pinchStep, type Pt, type Tap } from './gestures';
import { createPinchGuard, createWheelReader, inGesturePinch, setGesturePinch, wheelSample } from './wheel';
import { mapTextBoxes, passAt, pickLabelAt } from './mapPick';
import { ownersAt } from '../gen/civ/timeline';
import { faithAt } from '../gen/civ/religion';
import { filterChronicle, interventionOutcome } from '../gen/civ/chronicle';
import { fullChronicle } from '../gen/civ/religionText';
import { takeRewriteNote, type RewriteNote } from './rewriteStore';
import { AssistantPanel, PreviewBanner } from './Assistant';
import { astRoom, closeAssistant, useAstOpen } from './astPanel';
import { PREVIEW_EDIT_BLOCK, exitPreview, getAssistant, newConversation, sameInBoth, setTrialRunner, stopAsk, syncAssistantWorld, useAssistantPreview } from './assistantStore';
import { closeBookReader, closeHistoryBook, stopBook, useBookReader } from './bookStore';
import { getNav, isNavState, navAdopt, navBack, navLayer, navReplace, navSettled, navTitle, navTo, navUrl, startNav, type NavHooks, type NavInfo, type NavState } from './nav';
import { applyLayer as applyNavLayer, layerNow } from './navView';
import { useAiOn } from '../ai/client';
import { Globe, getGlobeOn, setGlobeOn, useGlobeOn, type GlobeApi } from './Globe';
import { setupAi } from '../ai/setup';
import { ToastBar, clearToast, showToast } from './Toast';
import { DRAFT_SEG, FirstHint, HoverCard, MapBar, MapControls, OldSiteBadge, PhoneButtons, hintSeen, markHintSeen } from './Corners';
import { frozenResult, noteMapSum, offerSnapshot, startResults, toldFrozen } from './resultStore';
import { FrozenAsk, askSaveAsNew, closeSaveAsNew, setSaveAsNew } from './FrozenWorld';
import { copyNotes } from '../ai/library';
import { BETA_SITE, OLD_SITE, OWN_KEY, oldSiteFor, oldSiteNote, openInLatest, openOriginal, plainSave } from './oldSite';
import type { ToastAction } from './toastStore';
import { Sidebar } from './Sidebar';
import { PhoneSheet } from './PhoneSheet';
import { useLayerThumbs } from './LayerPopover';
import { WorldOverview } from './WorldOverview';
import { hoverInfo, probeLines, type HoverInfo } from './hoverInfo';
import {
  FILL_KEYS,
  baseDark,
  baseLook,
  baseName,
  baseOf,
  baseThumb,
  fillOf,
  fillShow,
  layerOf,
  layerParts,
  paintLook,
  writeMapView,
  type BaseId,
  type FillId,
  type MapLayer,
  type MapView as BaseFill,
  type SatLook,
  type Style,
  type ThumbId,
} from './mapLayers';
import type { SurfaceLook } from '../render/surface';
import {
  TerrainOverlay,
  getTerrainTool,
  pageOf,
  setTerrainTool,
  setTerrainWrap,
  setTerrainProbe,
  terrainClick,
  terrainDown,
  terrainMove,
  terrainUp,
  terrainCancel,
  terrainStroking,
  useTerrainTool,
  type TerrainStatus,
} from './TerrainTools';
import { SourceLayer, beginImport, isImageFile, startImport, useImportOn, useSourceView } from './ImportImage';
import { NewWorldDialog, type NewWorldInit, type NewWorldMode, type NewWorldStart } from './NewWorldDialog';
import { randomSeedValue, type HomeStart } from './homeStart';
import { WORKER_URL } from './workerUrl';
import { closeUpheaval, getUpUi, setUpRunner, takeUpPreview, timelineAfterResim, undoUpOp, upCancel, upClick, upDown, upMove, upUp, upheavalName, useUpUi } from './upheavalStore';
import { UpheavalHint, UpheavalOverlay } from './UpheavalPanel';
import { PendingTray } from './PendingTray';
import { getPending, removePending, takePendingBatch } from './pendingStore';
import { dismissing, tookDismissClick } from './dismissClick';
import { makeFlagView, setFlagView, useFlagPreview } from './flagStore';
import { setFilmSource, setFilmViewport } from './filmSource';
import { closeFilm, getFilm, useFilm } from './filmStore';
import { FilmPanel } from './FilmPanel';
import { FilmStage } from './FilmStage';
import { LongPanel } from './LongPanel';
import { LongStage } from './LongStage';
import { noteGenSpeed } from './genSpeed';
import { cancelTimeout, holdMark } from './holdMark';
import { getNewView } from './newViewStore';
import { chosenGallery, getPresets, pickSharedPreset, rememberLast, type SharedPreset } from './presetStore';
import { diagBeat, recordWorkerError, setDiagContext } from '../diag/watch';

type Replay = { w: number; h: number; frames: Uint8ClampedArray[]; mya: number[]; idx: number };

/** 作品墙那一页(id = '')/ 一个作品的网址:世界的种子、参数这些去掉,图层、投影这些看法留着 */
function writeGalleryUrl(id: string) {
  navUrl(galleryHref(location.pathname, location.search, id, HOME_DROP));
}

/**
 * 作品墙盖在我的世界的位置上(和分享停了那一页一样):
 *   list  作品墙那一页(preset = 开着的新建参数作品,打开它的网址时)
 *   work  打开一个作品的网址:正在取 / 撤下了 / 取不到
 *   map   地图作品:整屏一颗星球
 * 世界作品打开就是平常的世界(只是看看,左上一条写作品;见 workFor)
 */
type WallView = { kind: 'list'; preset?: GalleryItem } | { kind: 'work'; id: string; state: 'loading' | 'gone' | { error: string } } | { kind: 'map'; work: GalleryItem };

/** 作品墙上的作品另存时写进存档的出处:作品的署名、作品名、作品的网址 */
function workOrigin(w: Pick<GalleryWork, 'id' | 'by' | 'title'>): SaveOrigin {
  return { ...(w.by ? { by: w.by } : {}), title: w.title, url: workLink(w.id), gallery: w.id };
}

/**
 * 换了底图 / 填色 / 卫星画法:写进网址(map=、fill=、sat=;去掉旧的 style=、layer=,civ= 里的国家 / 民族 / 信仰开关交给填色管),
 * 刷新、复制网址都还在
 */
function writeViewUrl(v: { base: BaseId; fill: FillId; sat: SatLook }) {
  const next = `?${writeMapView(new URLSearchParams(location.search), v)}`;
  if (next !== location.search) navUrl(next);
}

/** 底图在缓存里的键:手绘 / 写实(经典 = realistic,其余 realistic:画法)/ data:数据图层 */
export function baseKeyOf(style: Style, layer: LayerId, look: SurfaceLook): string {
  if (style === 'data') return `data:${layer}`;
  if (style === 'realistic') return look === 'classic' ? 'realistic' : `realistic:${look}`;
  return style;
}

/**
 * 新建中的世界让生成线程顺手画好的写实像素层(见 worker.ts 的 paint):新建界面的星球贴的是卫星画法 sat 那一种
 * (studioBase 的「实景」);地图现在的底图(key,baseKeyOf 的键)是写实的另一种画法的,那一种也画
 */
function paintLooks(key: string, sat: SurfaceLook): SurfaceLook[] {
  const look = key === 'realistic' ? 'classic' : key.startsWith('realistic:') ? (key.slice(10) as SurfaceLook) : null;
  return look && look !== sat ? [sat, look] : [sat];
}

/** 一个要打开的世界:生成(或直接用正在看的这一个)→ 套上修改 → 交给 saveStore 自动存 */
interface Target {
  id: string;
  kind: WorldKind;
  params: WorldParams;
  edits: WorldEdits;
  /** 已经存下的修改(套上的和它是同一个对象就不重写) */
  saved?: WorldEdits;
  title?: string;
  /** 新建中、作者还没动过(不存) */
  pristine?: boolean;
  /** 以某个世界为底稿新建 */
  base?: DraftBase | null;
  /** 换成存档里的投影和中央经线(undefined = 不动;null = 等距圆柱、0°) */
  view?: SaveView | null;
  /** 从哪打开的(生成完的提示按它说) */
  from?: 'file' | 'link' | 'stored' | 'restore' | 'url';
  /** 网址里带的生成器版本(from = 'url':打开带种子的网址) */
  gen?: number;
  /** 打开的存档(核对版本、地形) */
  save?: SaveFile;
  /** 读档时的警告 */
  warnings?: string[];
  /** 从分享短链接打开的:它的码(还没存进我的世界时留在网址里,刷新再取一次,看到分享的人最新的改动) */
  shareCode?: string;
  /** 从作品墙打开的世界作品:作品编号(还没存进我的世界时留在网址里,刷新再取一次) */
  gallery?: string;
  /** 分享链接带着的"打开时看哪"(停在哪一年、选中什么、镜头;gen/savefile.ts 的 SaveMoment) */
  moment?: SaveMoment | null;
  /** 底稿出处(存档里带着的;打开别人的分享短链接时是那个链接,改了另存时写进去) */
  origin?: SaveOrigin | null;
  /** 新建时选的照手绘图生成(还没照图长出星球时靠它认;存下以后看草图里有没有那张图) */
  mode?: 'image';
  /**
   * 在旧版本建的世界的地图上打造文明:那个世界存的地形校验。生成出来的地图和它对不上(现在的版本算出来不一样了)就不让打造
   */
  mapCheck?: string;
  /**
   * 照故事找世界选中的一个结果(新建中的世界换成它):推文明带上拓荒、起源、「天灾」(新建界面平时一律按默认推),
   * 和搜的时候推的一模一样
   */
  fullCiv?: true;
}

/** 新建中的世界是哪一种:照手绘图(选的就是它,或者草图里有照着长的图;旧的没建完的世界也这样认)/ 随机 */
function draftModeOf(t: Target | null): NewWorldMode {
  // 在一张地图上打造文明(地图锁着):不管地图是不是照手绘图长的,都是「打造文明」那一页
  if (t?.edits.map) return 'random';
  return t && (t.mode === 'image' || !!t.edits.sketch?.image) ? 'image' : 'random';
}

/** 生成这张地图用的(参数、地形、草图):照故事找世界「用这个世界」以后,这几样变了就不再是找到的那个世界 */
function genSigOf(params: WorldParams, edits: Pick<WorldEdits, 'terrain' | 'sketch'>): string {
  return JSON.stringify([worldKey(params), edits.terrain, edits.sketch ?? null]);
}

/** 新建中的世界现在的样子(参数、修改、名字),比较动没动过用 */
function draftSig(params: WorldParams, edits: WorldEdits, title?: string): string {
  // 地图的校验值是生成完自动记上的,不算动过
  const e = edits.map?.sum === undefined ? edits : { ...edits, map: { ...edits.map, sum: undefined } };
  return JSON.stringify([worldKey(params), e, title ?? '']);
}

/** 新建时只定了推演年数(3000 = 什么都没有)、拓荒(默认 = 什么都没有)的修改 */
function yearsEdits(endYear: number | undefined, frontier?: Frontier): WorldEdits {
  const y = cleanEndYear(endYear);
  const f = cleanFrontier(frontier);
  return y || f ? { ...EMPTY_EDITS, ...(y ? { endYear: y } : {}), ...(f ? { frontier: f } : {}) } : EMPTY_EDITS;
}

/** 一个新建中的世界(还没动过) */
function draftTarget(params: WorldParams, base: DraftBase | null = null, edits: WorldEdits = EMPTY_EDITS, title?: string): Target {
  return { id: newWorldId(), kind: 'draft', params, edits, pristine: true, base, title };
}

/**
 * 读档提示条上的按钮:最新版里打开旧版本的世界 =「看原样」(到那一版的旧网站里看,新页面;没有那一版的旧网站就不放);
 * 旧网站里打开更新的版本存的 =「到最新版打开」。orig:这个世界原来那一份
 */
function versionAction(orig: SaveFile | null): ToastAction | undefined {
  if (!orig) return undefined;
  if (OLD_SITE !== null) {
    if (!(orig.generator > GENERATOR_VERSION)) return undefined;
    return { label: '到最新版打开', act: 'open-latest', onClick: () => void openInLatest(orig).then((ok) => ok || openFailed()) };
  }
  const site = oldSiteFor(orig.generator);
  if (!site) return undefined;
  return { label: '看原样', act: 'see-original', onClick: () => void openOriginal(orig).then((ok) => ok || openFailed(site.href)) };
}

/** 交不过去(浏览器太旧,压缩不了存档):说一声怎么自己打开 */
function openFailed(site?: string) {
  notify({ kind: 'error', text: '这个浏览器打不开', more: [site ? `请把世界存成文件，到 ${site} 打开` : '请把世界存成文件，到最新版打开'] });
}

/** 存着的一个世界(刷新页面回到它时投影照网址,不换) */
function storedTarget(w: StoredWorld, from: 'stored' | 'restore'): Target {
  return {
    id: w.id,
    kind: w.draft ? 'draft' : 'created',
    params: w.save.params,
    edits: w.save.edits,
    saved: w.save.edits,
    title: w.save.title,
    base: w.base ?? null,
    pristine: false,
    view: from === 'restore' ? undefined : (w.save.view ?? null),
    from,
    save: w.save,
    origin: w.save.origin ?? null,
  };
}

/**
 * 存在"我的世界"里、旧版本建的世界(打开时先找它那一版的原件,照原样打开):存着的那份存档;别的 = null。
 * 从文件打开、和存着的一模一样的(读档时认成了同一个)也算
 */
function oldStored(t: Target): SaveFile | null {
  if (t.kind !== 'created') return null;
  const w = loadWorld(t.id);
  if (!w || w.draft || !(w.save.generator < GENERATOR_VERSION)) return null;
  // 从文件打开、认成存着的这一个:文件也得是那一版的(更新版本的文件照文件里的版本打开)
  if (t.save && t.save.generator !== w.save.generator) return null;
  return worldKey(w.save.params) === worldKey(t.params) && JSON.stringify(w.save.edits) === JSON.stringify(t.edits) ? w.save : null;
}

/** 存档原文里记的生成器版本(读不出 = null) */
function genOfText(text: string): number | null {
  const r = parseSave(text);
  return r.ok ? r.save.generator : null;
}

/** 网址里带种子的(别人发的网址、截图脚本):直接看这个世界,先不存,改了才存 */
function visitTarget(params: WorldParams, gen: number | null = null): Target {
  const t: Target = { id: newWorldId(), kind: 'visit', params, edits: EMPTY_EDITS };
  return gen === null ? t : { ...t, from: 'url', gen };
}

/** 朋友的预设链接打开的新建弹窗:第 2 步(随机生成),参数照链接填好;没带种子的随机给一个 */
function presetDialog(p: SharedPreset): { init: NewWorldInit; shared: SharedPreset } {
  return { init: { mode: 'random', params: { ...p.params, seed: p.seed ?? randomSeedValue() }, step: 2, endYear: p.endYear }, shared: p };
}

/**
 * 打开网页时去哪(只算一次):
 *   分享短链接(s=)    → 先是一页空白,去服务器取存档;取到了打开那个世界,停了显示"这个分享已经停止了"
 *   作品墙(gallery=)  → 作品墙那一页;带作品编号的先是一页空白,取到了打开那个作品,撤下了显示"这个作品已经撤下了"
 *   分享链接(#)       → 那个世界(先按网址生成,解开以后套上修改)
 *   w=世界编号(存着)   → 这个世界(没建完的回到新建);
 *                        这一步记的就是这个世界(刷新、按后退 / 前进从别的网址回来),现在不在了(在别的页面里删掉了)
 *                        → 我的世界,提示删掉了(gone = 世界名;网址里有 w= 就是存过)
 *   new=1             → 新建(网址里的种子、参数)
 *   new=image         → 我的世界 + 新建弹窗停在照手绘图选图那一步(照图新建还没长出星球时刷新)
 *   带种子的网址       → 直接看这个世界(改版前存过的就回到那个存档)
 *   都没有             → 我的世界(第一次来是空的那一页:一颗地球、一句话、「新建世界」;点了才生成星球);
 *                        # 后面是朋友的预设链接(#preset=)时,上面开着新建弹窗第 2 步、参数照链接填好(presetDialog)
 */
function firstRoute(init: ReturnType<typeof readUrl>): { stage: Stage; target: Target | null; gone?: string; dialog?: NewWorldInit } {
  const q = new URLSearchParams(location.search);
  if (init.shortShare !== null && !init.share) return { stage: 'home', target: null };
  // 作品墙那一页、作品的网址(世界作品只是看看、还没存下时刷新,网址里也是它):先停在我的世界的位置,去服务器取
  if (init.gallery !== null && !init.share) return { stage: 'home', target: null };
  if (init.share) return { stage: 'world', target: visitTarget(init.params) };
  const w = q.get('w');
  const stored = isWorldId(w) ? loadWorld(w) : null;
  // 只存了地图的:不当世界打开,回到我的世界的「地图」页签、选中它
  if (stored?.map) {
    showMapInWorlds(stored.id);
    return { stage: 'home', target: null };
  }
  if (stored) return { stage: stored.draft ? 'draft' : 'world', target: storedTarget(stored, 'restore') };
  const was: unknown = history.state;
  if (isWorldId(w) && isNavState(was) && was.page !== 'home' && was.id === w) return { stage: 'home', target: null, gone: was.title ?? '' };
  // 这一步记的世界存着,网址是存下之前的那一版(开着卡片时改了第一笔才存下,退回来的这一步网址里还没有 w=):打开存着的
  const mine = !isWorldId(w) && isNavState(was) && was.page === 'world' && was.id ? loadWorld(was.id) : null;
  if (mine && !mine.draft) return { stage: 'world', target: storedTarget(mine, 'restore') };
  if (q.get('new') === '1') return { stage: 'draft', target: draftTarget(init.params, null, yearsEdits(init.years)) };
  // 照手绘图新建、还没照图长出星球(图不存,刷新就没了):回到我的世界,弹窗停在照手绘图的第 2 步(参数照网址)重新选图
  if (q.get('new') === 'image') return { stage: 'home', target: null, dialog: { mode: 'image', params: init.params, step: 2, endYear: init.years } };
  if (q.has('seed')) {
    // 改版前自动存的世界:那时的网址只带种子、参数,刷新照旧回到它(带 gen= 的是改版后的网址,不是它)
    const old = init.gen === null ? legacyWorld(init.params) : null;
    if (old) return { stage: old.draft ? 'draft' : 'world', target: storedTarget(old, 'restore') };
    return { stage: 'world', target: visitTarget(init.params, init.gen) };
  }
  return { stage: 'home', target: null };
}

/** 浏览器后退记的这一步是哪个画面(nav.ts):我的世界 / 新建(哪颗星球)/ 某个世界 */
function navInfo(stage: Stage, t: Target | null | undefined): NavInfo {
  if (stage === 'home' || !t) return { page: 'home' };
  return stage === 'draft' ? { page: 'draft', id: t.id, seed: t.params.seed, title: t.title } : { page: 'world', id: t.id, title: t.title };
}

/** 网址里的看法(画风、图层、投影、中央经线、经纬网、等值线):不算一步,按后退 / 前进时照现在的(nav.ts 的 url) */
const VIEW_KEYS = ['style', 'layer', 'map', 'fill', 'sat', 'civ', 'proj', 'view', 'lon', 'grat', 'iso'];
function keepView(from: string, to: string): string {
  const a = new URL(from);
  const b = new URL(to);
  for (const k of VIEW_KEYS) {
    const v = a.searchParams.get(k);
    if (v === null) b.searchParams.delete(k);
    else b.searchParams.set(k, v);
  }
  return b.href;
}

/** 还在 b 那个画面(同一个画面里开卡片多记的几步也算);去解开 / 取回分享的世界,拿到时看一眼 */
function sameScreen(a: NavState | null, b: NavState | null): boolean {
  return !!a && !!b && a.bare === b.bare && a.page === b.page && a.id === b.id;
}

/** 按后退 / 前进要回的世界已经删掉了(停在我的世界) */
function goneToast(title: string | undefined) {
  showToast({ id: 'nav-gone', kind: 'warn', text: `回不到「${title || '未命名世界'}」`, more: ['这个世界已经删掉了'] });
}

/** 新建时能看的样式(不用历史的那几种) */
const STUDIO_LAYERS: MapLayer[] = STUDIO_STYLES.map((x) => x.id);

/** 新建时能看这组底图和填色(填色要有历史;新建界面的样式里没有地理图、白模和几种数据底图) */
function studioView(v: { base: BaseId; fill: FillId }): boolean {
  if (v.fill !== 'none') return false;
  return v.base === 'satellite' || v.base === 'fantasy' || STUDIO_LAYERS.includes(v.base as MapLayer);
}


/**
 * 把世界写进网址:种子 + 参数(和默认值相同的省略,别人打开是同一颗星球);存着的加 w=编号,新建中还没存的加 new=1
 * (照手绘图新建、还没照图长出星球的加 new=image)
 */
function writeWorldUrl(t: Target) {
  const q = new URLSearchParams(location.search);
  for (const k of Object.keys(DEFAULT_PARAMS) as (keyof WorldParams)[]) {
    if (k === 'seed' || t.params[k] !== DEFAULT_PARAMS[k]) q.set(k, String(t.params[k]));
    else q.delete(k);
  }
  q.delete('w');
  q.delete('new');
  q.delete('s');
  q.delete('gallery');
  q.delete(OWN_KEY);
  // 分享短链接、作品墙打开的、还没存进我的世界:码 / 作品编号留在网址里(刷新再取一次)
  if (t.shareCode && t.kind === 'visit' && !isStored(t.id)) q.set('s', t.shareCode);
  if (t.gallery && t.kind === 'visit' && !isStored(t.id)) q.set('gallery', t.gallery);
  // 存着的记录还是换参数之前的(新建中换了种子、参数,正在生成):先不指向它,存好了再换成 w=
  const w = isStored(t.id) ? loadWorld(t.id) : null;
  if (w && worldKey(w.save.params) === worldKey(t.params)) q.set('w', t.id);
  else if (t.kind === 'draft') q.set('new', draftModeOf(t) === 'image' && !t.edits.sketch?.image ? 'image' : '1');
  // 还没存下的新建:弹窗里开的推演年数也写上(存下以后在存档里)
  const years = q.has('new') ? cleanEndYear(t.edits.endYear) : undefined;
  if (years) q.set('years', String(years));
  else q.delete('years');
  // 生成器版本:复制这个网址发给别人,以后版本更新了对方打开会说清变了什么。
  // 网址来自更新的版本(页面是旧的)就留着那个号:刷新还是旧页面照样提示,换到新页面就对上了。
  // 新建中还没存的(new=1)不带:打开这种网址是接着新建,用的总是现在的版本
  if (q.has('new')) q.delete(GEN_KEY);
  else q.set(GEN_KEY, String(t.gen !== undefined && t.gen > GENERATOR_VERSION ? t.gen : GENERATOR_VERSION));
  const next = `?${q}`;
  if (next !== location.search) navUrl(next);
}

/** 回到"我的世界"时网址里去掉的:这个世界(种子、参数、编号、年份……) */
const HOME_DROP = [...Object.keys(DEFAULT_PARAMS), 'w', 'new', 'years', 's', GEN_KEY, 'civYear', 'play', 'chron'];

/** 回到"我的世界":网址里去掉这个世界(种子、参数、编号、年份……)、作品墙,留着图层、投影这些看法 */
function writeHomeUrl() {
  const q = new URLSearchParams(location.search);
  for (const k of [...HOME_DROP, 'gallery']) q.delete(k);
  const rest = q.toString();
  navUrl(rest ? `?${rest}` : location.pathname);
}

/** 创建完要不要从第 0 年起放一遍历史(网址给了 play=0、无头浏览器里不放;play=1 一定放) */
function storyOk(): boolean {
  const play = new URLSearchParams(location.search).get('play');
  if (play === '0') return false;
  if (play === '1') return true;
  return !(typeof navigator !== 'undefined' && navigator.webdriver);
}

/** 主线程最多留多少块各段的主图补丁(换了地形大事、撤销回去时用得上;先丢最早的) */
const PATCH_KEEP = 24;
/** 后台线程交历史之前先交的几段(src/civParts.ts);换了线程就清掉 */
const civParts = new CivPartInbox();
/** 同一个世界画好的整张图留几张(地形大事前后各一张;见下面的 mapsOf) */
const MAP_KEEP = 2;
/** 时间轴换段前在后台备那一段的地图的活名(detailJobs.ts) */
const ERA_WARM_JOB = 'era-warm';
/** 再推好了的提示条停多久(和加干预以后的一样);推之前那一份(撤销用)多留一会儿再放掉 */
const EXTEND_TOAST_MS = 7000;
const EXTEND_UNDO_MS = EXTEND_TOAST_MS + 1000;

/** 请求里带的地形大事(没有 = 不带) */
const upsOpt = (u: readonly Upheaval[] | undefined) => (u?.length ? { upheavals: [...u] } : {});
/** 推文明时带的地名风格(自动 = 不带) */
const namesOpt = (names: NameMix | undefined) => (names ? { names } : {});
/** 推文明时带的推演年数(3000 = 不带) */
const yearsOpt = (endYear: number | undefined) => (endYear ? { endYear } : {});
/**
 * 这一步要推到第几年(3000 = undefined):新建界面里只看星球,一律先推 3000 年(换种子、调参数不用等);
 * 创建以后再按世界自己的推演年数接着推(见下面重推的那段)
 */
const yearsFor = (draft: boolean, edits: Pick<WorldEdits, 'endYear'>) => (draft ? undefined : cleanEndYear(edits.endYear));
/** 推文明时带的拓荒、起源、文明种子、「天灾」(默认 = undefined) */
type CivSetup = { frontier?: Frontier; origins?: Origins; civSeed?: number; calamity?: Calamity };
const setupOpt = (s: CivSetup | undefined) => ({
  ...(s?.frontier ? { frontier: s.frontier } : {}),
  ...(s?.origins ? { origins: s.origins } : {}),
  ...(s?.civSeed !== undefined ? { civSeed: s.civSeed } : {}),
  ...(s?.calamity ? { calamity: s.calamity } : {}),
});
/**
 * 这一步带的拓荒、起源、文明种子、「天灾」:拓荒、起源、天灾和推演年数一样,新建界面里只看星球、一律按默认推,创建以后按世界自己的;
 * 文明种子新建界面里就带着(星球上的地名、选起源时的州名照它长)
 */
function setupFor(draft: boolean, edits: Pick<WorldEdits, 'frontier' | 'origins' | 'civSeed' | 'calamity'>): CivSetup | undefined {
  const civSeed = cleanCivSeed(edits.civSeed);
  if (draft) return civSeed !== undefined ? { civSeed } : undefined;
  const frontier = cleanFrontier(edits.frontier);
  const origins = cleanOrigins(edits.origins);
  const calamity = cleanCalamity(edits.calamity);
  return frontier || origins || civSeed !== undefined || calamity
    ? { ...(frontier ? { frontier } : {}), ...(origins ? { origins } : {}), ...(civSeed !== undefined ? { civSeed } : {}), ...(calamity ? { calamity } : {}) }
    : undefined;
}
const sameSetup = (a: CivSetup | undefined, b: CivSetup | undefined) =>
  sameFrontier(a?.frontier, b?.frontier) && sameOrigins(a?.origins, b?.origins) && a?.civSeed === b?.civSeed && a?.calamity === b?.calamity;

/** 改名里有几处在这份历史里找不到(找不到的先保留着) */
const lostRenames = (civ: Civ, names: Record<string, string>) => Object.keys(names).filter((k) => !resolveKey(civ, k)).length;
/** 打开世界时提示条上说改名对不上的那一句 */
const lostRenamesNote = (n: number) => `${n} 处改名没对上,先保留`;

/** 结束那一年现存几国(我的世界的卡片上写;没长出文明 = 0) */
function aliveAtEnd(civ: Civ): number {
  return civ.viable ? civ.polities.filter((x) => polityAlive(x, civ.endYear)).length : 0;
}

/** 线程上的活,问题记录里的说法 */
const WORK_LABEL: Partial<Record<WorkerRequest['type'], string>> = {
  generate: '生成世界',
  resim: '推演历史',
  civOnly: '推演历史',
  history: '回放世界形成',
  trial: '助手试推演',
  upPreview: '预览地形大事',
};

/** 逐年推演切到了别的一支:from = 原来那支的编号,fromRef / toRef = 两支在句子里的叫法,year = 切到的那一支的"现在" */
interface SwitchNote {
  from: number;
  fromRef: string;
  toRef: string;
  year: number;
}
/** 切到别的一支了(停在那一支的"现在"):说一声,带「切回」原来那支 */
function switchedToast(sw: SwitchNote) {
  showToast({
    id: 'step-switched',
    kind: 'ok',
    text: `已切到${sw.toRef}，${yearFull(sw.year, getEdits().era)}`,
    action: { label: `切回${sw.fromRef}`, act: 'step-switch-back', onClick: () => stepwiseActions()?.switchBranch(sw.from) },
    ttl: 8000,
  });
}
/** 切支线的时候,修改里已经是切到的那一支,地图、面板上还是原来那支:先不许下令、改名(用的键可能指到那一支里别的东西) */
const SWITCH_EDIT_BLOCK = '正在切到别的一支，切完再改';

// 帮手模式(作品墙的后台在看不见的框里打开网站画封面、列名字):和主程序同一份下载,用到的地图、推演代码不另下(Boot.tsx 叫)
export { startGalleryHelper } from './galleryHelper';

/** fromHome:打开网站时先出来的首页(HomeShell.tsx)上点了要离开首页的事,挂上以后接着做(见 Boot.tsx) */
export function App({ fromHome }: { fromHome?: HomeStart } = {}) {
  const init = useMemo(readUrl, []);
  /** 打开网页时去哪:我的世界 / 新建 / 某个世界(见 firstRoute) */
  const route = useMemo(() => firstRoute(init), [init]);
  /** 进新建时换掉的底图和填色(填色要有历史);建好 / 打开别的世界时换回来 */
  const draftViewRef = useRef<{ base: BaseId; fill: FillId } | null>(null);
  // 网址里的投影、中央经线、经纬网:第一次渲染之前放进 store(等距圆柱的视图在世界出来以后再转过去,见 pendingLon)
  const start = useState(() => {
    setProjection(init.proj);
    if (init.lon !== null) publishMapCenter(init.lon);
    setGraticule(init.grat > 0);
    if (isGraticuleStep(init.grat)) setGraticuleStep(init.grat);
    setContourKind(init.iso);
    setStage(route.stage, route.target?.base ?? null);
    // 网址里给的(或默认的)底图和填色:国家 / 民族 / 信仰开不开跟着填色;新建时只看地形
    let mv: BaseFill | null = init.mapView;
    let { style, layer, surface } = init;
    // 新建:网址里给的是新建时能看的样式就照它,否则用卫星(填色要有历史;建好以后换回来)
    if (route.stage === 'draft') {
      const now = mv ?? { base: baseOf(style, layer, surface), fill: fillOf(getCivShow()) };
      draftViewRef.current = { base: now.base, fill: now.fill };
      if (!studioView(now)) {
        mv = { base: 'satellite', fill: 'none' };
        style = 'realistic';
        surface = init.sat;
        writeViewUrl({ ...mv, sat: init.sat });
      }
    }
    if (mv) setCivShow(mv.resources ? { ...fillShow(mv.fill), resources: true } : fillShow(mv.fill));
    return { style, layer, surface, sat: init.sat };
  })[0];
  const graticule = useGraticuleLines();
  const contourKind = useContourKind();
  const projection = useProjection();
  const curved = isCurved(projection);
  const mapCenter = useMapCenter();
  const projMoving = useMapMoving() && curved;
  const [params, setParams] = useState<WorldParams>(route.target?.params ?? init.params);
  const [style, setStyle] = useState<Style>(start.style);
  const [layer, setLayer] = useState<LayerId>(start.layer);
  /** 写实底图的画法(经典卫星 / 卫星 / 地理图 / 白模;不是写实底图时不用) */
  const [surface, setSurface] = useState<SurfaceLook>(start.surface);
  /** 卫星记着的画法(经典 / 细节):换到别的底图再换回卫星还是它 */
  const [satLook, setSatLook] = useState<SatLook>(start.sat);
  // 填色(不填 / 国家 / 民族 / 信仰 / 时代 = 文明层的开关)
  const civShow = useCivShow();
  /** 写实底图实际铺的那一份:地理图上叠了填色时是褪色的那一份(paintLook);缓存的键、画图都按它 */
  const paintedLook = paintLook(surface, fillOf(civShow));
  const { stage, base: stageBase } = useStage();
  const draft = stage === 'draft';
  const home = stage === 'home';
  /** 新建界面(Studio)创建以后还没走完:1 = 星球展开成平常的地图,2 = 新建界面淡出(底下平常的地图露出来) */
  const [studioOut, setStudioOut] = useState<0 | 1 | 2>(0);
  /** 照故事找世界那一页开着(新建中,FinderPage.tsx):新建界面先收起,平常的地图露出来 */
  const finder = useFinder();
  const finderOn = draft && finder.open;
  /** 新建界面盖着整页:深色、太空底,平常的地图藏起来(摊平改地形时铺在中间那块) */
  const studioOn = (draft && !finderOn) || studioOut === 1;
  const studioFlat = useStudioFlat();
  // 宽屏左边的卡片收起了(sideStore.ts):新建世界那一步左边是新建世界的卡片,不算收起(sideRoom 照常让出它)
  const sideUi = useSide();
  setSideHold(stage !== 'world');
  /** 正在打开 / 已经打开的世界(生成完按它套上修改、交给自动存) */
  const targetRef = useRef<Target | null>(route.target);
  /**
   * 新建中、照平常的规矩推历史(先推 3000 年、拓荒起源天灾按默认):照故事找世界选中的结果不算(它按自己的推演年数、拓荒、起源、天灾推,
   * 和搜的时候一样,见 Target.fullCiv)
   */
  const plainDraft = () => getStage().stage === 'draft' && !targetRef.current?.fullCiv;
  /** 新建中的名字(卡片上的输入框;打开没建完的世界时是它存的名字) */
  const [draftTitle, setDraftTitle] = useState(route.target?.kind === 'draft' ? (route.target.title ?? '') : '');
  /** 「新建世界」弹窗:开着没有、从哪一步开始(刷新了照手绘图还没长出星球的新建:停在它选图那一步) */
  /** 打开网页时的朋友的预设链接(#preset=…):解开的结果(没有 = null) */
  const presetLink = useState(() => {
    const r = init.preset ? decodePresetHash(init.preset) : null;
    if (r?.ok) pickSharedPreset(r.preset);
    return r;
  })[0];
  const [newDlg, setNewDlg] = useState<{ init?: NewWorldInit; shared?: SharedPreset; stamp?: number } | null>(() =>
    route.dialog ? { init: route.dialog } : presetLink?.ok && route.stage === 'home' ? presetDialog(presetLink.preset) : null,
  );
  /** 生成出来的世界和主图(地形大事以前的;地图上画的是 data:时间轴那一段的) */
  const [baseData, setData] = useState<{ world: World; raster: Raster } | null>(null);
  /** 地形大事以后各段的世界(后台线程交来的;没有大事 = null)、各段主图的补丁(后台慢慢铺好交来;eras.ts) */
  const [eraMaps, setEraMaps] = useState<EraMaps | null>(null);
  const eraPatches = useRef(new Map<string, RasterPatch | null>());
  const [patchVer, setPatchVer] = useState(0);
  // 生成出来的文明("原始 civ")+ 用户的改名(editsStore)= 界面用的 civ。改名只重算这一步,不发给后台线程
  const [rawCiv, setRawCiv] = useState<Civ | null>(null);
  const edits = useEdits();
  // 助手的"先在地图上看看":地图、卡片、时间轴换成试推演的历史(州和宜居度和现在共用;作者的世界没动,rawCiv 还是原来的)
  const astOpen = useAstOpen();
  const preview = useAssistantPreview();
  const previewRaw = preview?.raw ?? null;
  /** 时间轴现在在第几段(地形大事以后,地图、州、地名、道路跟着换;eras.ts) */
  const eraWant = useEraIndex(previewRaw ?? rawCiv);
  /** 地图该画的那一段:那一段的主图还在后台铺时,先是前面铺好了的那一段(历史、世界、主图三样对得上) */
  // eslint-disable-next-line react-hooks/exhaustive-deps -- patchVer:后台交来新的补丁时重算
  const eraNext = useMemo(() => eraShown(eraMaps, eraPatches.current, eraWant), [eraMaps, patchVer, eraWant]);
  /** 地图上画着的是哪个世界(原主图那一份)、哪份各段世界的第几段 */
  const eraAt = useRef<{ maps: EraMaps | null; base: object | null; k: number } | null>(null);
  /** 换段前在后台备好了的那一段(世界和主图那一份)、按哪种底图备的 */
  const eraWarm = useRef<{ data: object; key: string } | null>(null);
  /** 地图缓存里有没有这一段的这种底图(渲染那里填上;有就直接换,不用备) */
  const eraCached = useRef<(d: object, key: string) => boolean>(() => false);
  const [warmVer, setWarmVer] = useState(0);
  const warmKey = baseKeyOf(style, layer, paintedLook);
  /**
   * 地图上实际画的那一段:换段(补丁刚到、拖时间轴跨过大事)时,那一段的整张底图、河、文明层先在后台分小步备好再换过去
   * (见下面的 ERA_WARM_JOB),不在换上那一下整张画;备的时候照旧画原来那一段(历史、世界、主图三样对得上)
   */
  // eslint-disable-next-line react-hooks/exhaustive-deps -- patchVer:后台交来新的补丁时重算;warmVer:备好了
  const eraK = useMemo(() => {
    const at = eraAt.current;
    const prev = at && at.maps === eraMaps && at.base === baseData ? at.k : null;
    if (prev === null || prev === eraNext || !baseData) return eraNext;
    // 那一段的主图还没拼:没备好(拼也在后台备的那几步里)
    const d = peekEraData(baseData, eraMaps, eraPatches.current, eraNext);
    const w = eraWarm.current;
    return d && ((w && w.data === d && w.key === warmKey) || eraCached.current(d, warmKey)) ? eraNext : prev;
  }, [eraMaps, patchVer, eraNext, baseData, warmVer, warmKey]);
  useLayoutEffect(() => {
    eraAt.current = { maps: eraMaps, base: baseData, k: eraK };
  }, [eraMaps, baseData, eraK]);
  // eslint-disable-next-line react-hooks/exhaustive-deps -- patchVer:后台交来新的补丁时重拼
  const data = useMemo(() => (baseData ? eraData(baseData, eraMaps, eraPatches.current, eraK) : null), [baseData, eraMaps, patchVer, eraK]);
  /**
   * 整段历史(最后一段的州、地名,套上改名):编年史这类按它算(见 Civ.history);后台线程按同样的改名算好了编年史的直接用。
   * 改了名、编年史还在分小块算的时候,先照旧显示改名以前的样子,算好再换上(chronicleHandoff.ts);realNames = 现在套着的那份改名
   */
  // 作者立的君主(干预"即位")套上人物卡上的名字
  const realNamed = useNamedHistory(rawCiv, edits.names, edits.characters);
  const realFull = realNamed?.full ?? null;
  const realNames = realNamed?.names ?? edits.names;
  // 试推演的编年史在换上之前已经分小块算好了(assistantStore.ts 的 showPreview)
  const previewFull = useMemo(() => (previewRaw ? namedHistory(previewRaw, preview!.names, getEdits().characters) : null), [previewRaw, preview?.names]);
  /** 地图上那一段的历史:那一段的州、地名、道路,套上改名;更早一段时挂上整段历史 */
  const eraView = (raw: Civ, full: Civ, names: Record<string, string>) => {
    const e = civAtEra(raw, eraK);
    return e === raw ? full : withHistory(applyNames(e, names), full);
  };
  /** 现在这个世界的历史(时间轴那一段的) */
  // eslint-disable-next-line react-hooks/exhaustive-deps -- eraView 只用到 eraK
  const realCiv = useMemo(() => (rawCiv && realFull ? eraView(rawCiv, realFull, realNames) : null), [rawCiv, realFull, eraK, realNames]);
  const shownRaw = useMemo(() => {
    const r = previewRaw ?? rawCiv;
    return r ? civAtEra(r, eraK) : null;
  }, [previewRaw, rawCiv, eraK]);
  // eslint-disable-next-line react-hooks/exhaustive-deps -- eraView 只用到 eraK
  const civ = useMemo(() => (previewRaw && previewFull ? eraView(previewRaw, previewFull, preview!.names) : realCiv), [previewRaw, previewFull, eraK, preview?.names, realCiv]);
  /** 照大纲推演的提示条上写名字用(套上改名的那一份) */
  const realCivRef = useRef(realCiv);
  realCivRef.current = realCiv;
  // 推演里作者的人物当的君主(编年史、世系图、国家卡片里点他的名字):打开作者的人物卡;人物卡删掉了照旧开推演人物卡
  const civForRedirect = useRef(civ);
  civForRedirect.current = civ;
  useLayoutEffect(() => {
    setSelectionRedirect((sel) => {
      if (sel.kind !== 'person') return sel;
      const a = civForRedirect.current?.people?.[sel.id]?.author;
      return a !== undefined && getEdits().characters?.some((c) => c.id === a) ? { kind: 'character', id: a } : sel;
    });
    return () => setSelectionRedirect(null);
  }, []);
  // 国旗(flagStore.ts):所有国家历代的旗,套上作者改过的和「换一面」「自己改」正在预览的那一面;历史和世界对不上(正在重新生成)时先不算。
  // 有地形大事的按第一件以前的地形配(拖时间轴跨过大事旗不跟着变,那以前的旗和没有大事时一样)
  const flagPreview = useFlagPreview();
  const flagGeo = useMemo(() => {
    const r = previewRaw ?? rawCiv;
    if (!r?.eras?.length || !baseData) return undefined;
    return { world: baseData.world, civ: applyNames(civAtEra(r, 0), previewRaw ? preview!.names : realNames) };
  }, [previewRaw, rawCiv, baseData, preview?.names, realNames]);
  const flagView = useMemo(
    () =>
      data && civ && civ.viable && civ.habitat.suitability.length === data.world.mesh.n ? makeFlagView(data.world, civ, edits.flags, flagPreview, flagGeo) : null,
    [data, civ, edits.flags, flagPreview, flagGeo],
  );
  useLayoutEffect(() => setFlagView(flagView), [flagView]);
  // 导出回放视频 / 故事长图:左边面板(手机:底部卡片)换成导出的选项
  const filmUi = useFilm();
  // 回放导出(视频、故事长图)按年份取那一段的世界、主图、历史(filmSource.ts);和地图上一样,那一段的主图还没铺好先用前一段
  // (预览这样凑合;导出等 ready 了再拍)
  useLayoutEffect(() => {
    const raw = previewRaw ?? rawCiv;
    const full = previewFull ?? realFull;
    if (!baseData || !raw || !full) return setFilmSource(null);
    const names = previewRaw ? preview!.names : realNames;
    const civs = new Map<number, Civ>();
    const lastK = eraIndex(raw, full.endYear);
    setFilmSource({
      full,
      ready: lastK === 0 || (!!eraMaps && eraReady(eraMaps, eraPatches.current, lastK)),
      at(year) {
        const k = eraShown(eraMaps, eraPatches.current, eraIndex(raw, year));
        const { world, raster } = eraData(baseData, eraMaps, eraPatches.current, k);
        const geo = civAtEra(raw, k);
        let civ = civs.get(k);
        if (!civ) civs.set(k, (civ = geo === raw ? full : withHistory(applyNames(geo, names), full)));
        return { k, world, raster, civ, geo };
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- patchVer:后台交来新的补丁时换一份(各段的主图跟着补上)
  }, [baseData, eraMaps, patchVer, previewRaw, rawCiv, previewFull, realFull, realNames, preview?.names]);
  // 导出时"换回原名"用的:AI 起的名字换回原来的(没有 AI 起的名字、助手"先看看"时 = null,导出菜单不问)
  const plainCiv = useMemo(
    () => (rawCiv && !previewRaw && aiNameKeys(edits).length ? applyNames(civAtEra(rawCiv, eraK), namesWithoutAi(edits)) : null),
    [rawCiv, eraK, previewRaw, edits],
  );
  /** 右侧详情面板开着(右下角的地球仪 / 缩放按钮让开它) */
  const selState = useSelection();
  // 右侧面板开着(选目标、下了令正在推演时面板藏起来,右下按钮回到原位)
  const panelUi = usePanel();
  const pickNow = usePolityPick();
  /** 地形大事的卡片开着(UpheavalPanel.tsx;和选中的东西的卡片在同一处) */
  const upOn = useUpUi().on;
  const panelOpen = (!!selState.sel || upOn) && !!civ && !pickNow && !panelUi.run;
  /** 窄屏(手机):底部的世界 / 详情卡片、时间轴胶囊、右上竖排按钮(phone.css);触屏:没有悬停卡片、右下不放 + −(用双指捏合) */
  const narrow = useNarrow();
  const coarse = useCoarse();
  const narrowRef = useRef(narrow);
  narrowRef.current = narrow;
  /** 生成进度(提示条"正在生成世界"):regen = 按新地形重新生成;seed = 正在生成的种子 */
  const [progress, setProgress] = useState<{ stage: string; pct: number; regen?: boolean; seed?: number } | null>(null);
  /** 悬停小卡片:内容 + 鼠标位置(视口坐标) */
  const [hover, setHoverState] = useState<{ info: HoverInfo; x: number; y: number; place?: 'above' | 'left' } | null>(null);
  // 选目标时鼠标下的可选对象:名牌反色(TargetPlates)
  const setHover = (h: { info: HoverInfo; x: number; y: number; place?: 'above' | 'left' } | null) => {
    setPickHover(h?.info.pick ?? -1);
    setHoverState(h);
  };
  // ---- 底图(手绘 / 卫星 / 地理图 / 白模 / 数据底图)× 填色(不填 / 国家 / 民族 / 信仰 = 文明层的开关) ----
  const mapBase = baseOf(style, layer, surface);
  const mapFill = fillOf(civShow);
  /** 旧的图层名(新建界面的样式、新建时的默认用) */
  const mapLayer = layerOf(style, layer, civShow);
  /** 地形画在写实底图上时用哪种画法(别的画风不看它) */
  const terrainLook: SurfaceLook = style === 'realistic' ? paintedLook : 'classic';
  const mapViewRef = useRef({ base: mapBase, fill: mapFill, sat: satLook });
  mapViewRef.current = { base: mapBase, fill: mapFill, sat: satLook };
  const theme = studioOn || baseDark(mapBase) ? 'dark' : 'light';
  // 挂在 body 下的弹窗(AI 设置、史书)也跟着换主题;画第一帧之前就换好(首次打开深色图层时不先闪一下浅色底)
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  /** 换底图 / 填色 / 卫星画法(没给的照旧) */
  const applyMapView = useCallback((patch: Partial<{ base: BaseId; fill: FillId; sat: SatLook }>) => {
    const v = { ...mapViewRef.current, ...patch };
    const b = baseLook(v.base, v.sat);
    setStyle(b.style);
    if (b.data) setLayer(b.data);
    if (b.look) setSurface(b.look);
    setSatLook(v.sat);
    setCivShow(fillShow(v.fill));
    mapViewRef.current = v;
    writeViewUrl(v);
  }, []);
  /** 按旧的图层名换(新建界面的样式;实景 = 卫星,用记着的画法) */
  const applyLayer = useCallback(
    (id: MapLayer) => {
      const { base, fill, resources } = layerParts(id);
      applyMapView({ base, fill });
      if (resources) setCivShow({ resources: true });
    },
    [applyMapView],
  );
  /** 第一次打开的操作提示(第一次拖动 / 缩放 / 点击之后不再出现) */
  const [hintOn, setHintOn] = useState(() => !hintSeen());
  const trashView = useTrashView();
  /** 分享短链接:正在取 / 停了 / 打不开(取到了 = null) */
  const [landing, setLanding] = useState<'loading' | 'gone' | { error: string } | null>(route.stage === 'home' && init.shortShare !== null && !init.share ? 'loading' : null);
  /** 作品墙那一页 / 正在打开的作品 / 地图作品(见 WallView;不在作品墙 = null) */
  const [wall, setWall] = useState<WallView | null>(() =>
    route.stage !== 'home' || init.gallery === null || landing ? null : init.gallery ? { kind: 'work', id: init.gallery, state: 'loading' } : { kind: 'list' },
  );
  /** 换了画面就作废还在取的作品(取回来时对一下) */
  const wallSeq = useRef(0);
  /** 这一页里打开过的世界作品:世界编号 → 作品(按后退 / 前进回到它时,左上那一条照旧) */
  const workItems = useRef(new Map<string, GalleryItem>());
  /** 正在看的世界是从作品墙打开的世界作品:那个世界的编号和作品(地图左上那一条;回作品墙、换了世界就不放) */
  const [workFor, setWorkFor] = useState<{ id: string; work: GalleryItem } | null>(null);
  /**
   * 打开别人分享的世界:地图下那条说明(这个世界的编号;点了"知道了"、改了存进我的世界以后不再显示)。
   * at = 链接带着"这一刻"、打开停在了那里:说明开头说清停在哪一年、选中的哪国(点了「从头放」就不再说)
   */
  const [sharedFor, setSharedFor] = useState<{ id: string; short: boolean; by: string; own: boolean; at?: { year: number; sel: ResolvedMoment['selected'] | null } | null } | null>(null);
  const touchRef = useRef(() => {});
  touchRef.current = () => {
    if (getStage().stage !== 'world') return;
    if (!hintOn) return;
    setHintOn(false);
    markHintSeen();
  };
  /** 鼠标最近在哪(视口坐标;地球仪的悬停只给像素,卡片位置用它) */
  const mouseAt = useRef<[number, number]>([0, 0]);
  const [replay, setReplay] = useState<Replay | null>(null);
  const [replayOn, setReplayOn] = useState(false);
  /** 最上面的屏幕层(文字层放在这里,见 CivLayer 的 labelsHost) */
  const [labelsHost, setLabelsHost] = useState<HTMLDivElement | null>(null);
  /** 放大后的文明细节层放在这一层屏幕层里(见 CivLayer 的 detailHost) */
  const [civDetailHost, setCivDetailHost] = useState<HTMLDivElement | null>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  /** 地形图、回放帧在右边接的那一份(左右无限拖动,见 mapWrap.ts) */
  const canvasCopyRef = useRef<HTMLCanvasElement>(null);
  const overlayCopyRef = useRef<HTMLCanvasElement>(null);

  const workerRef = useRef<Worker | null>(null);
  /** 助手的试推演:发给线程、还没回音的(编号 → 等着的那一次) */
  const trials = useRef(new Map<number, { resolve: (c: Civ) => void; reject: (e: Error) => void }>());
  const trialSeq = useRef(0);
  /** 发给当前线程、还没回音的活(生成世界 / 回放帧 / 重推文明)有几件 */
  const busyRef = useRef(0);
  /**
   * 其中线程能半路放下的(编辑地形时只换地形、不推历史的生成):后面来了新的世界,线程自己不算完它(回音 aborted),
   * 只有这种活在忙时换世界不用关掉线程重开(记着的网格、板块、整图都还在)
   */
  const softRef = useRef(new Set<number>());
  /** 线程在忙什么(问题记录用;闲下来 = null) */
  const workLabel = useRef<string | null>(null);
  const layerRef = useRef(layer);
  layerRef.current = layer;
  // 问题记录:出错、意外关闭时带上线程在忙什么、在看哪一年、哪个世界、哪个图层
  useEffect(() => {
    setDiagContext(() => ({
      doing: workLabel.current ?? undefined,
      year: getCivTime().year ?? undefined,
      world: genParams.current ? worldKey(genParams.current) : undefined,
      layer: layerRef.current,
    }));
    return () => setDiagContext(() => ({}));
  }, []);
  const reqId = useRef(0);
  // 改了名告诉后台线程(不排队、没有回音):正在推的那一次推完,编年史按现在的改名算,换上时不用再算一遍
  useEffect(() => {
    workerRef.current?.postMessage({ type: 'renames', id: reqId.current, names: edits.names } satisfies WorkerRequest);
  }, [edits.names]);
  /**
   * 照原样打开的旧世界(读存着的原件,不重新生成):正在读的是哪个世界、建它的生成器版本;
   * 原件读不出来、改成按新版生成的是哪个世界(提示条上说一句)。见 resultStore.frozenResult / worker 的 load
   */
  const frozenLoad = useRef<{ id: string; gen: number } | null>(null);
  const frozenBroken = useRef<string | null>(null);
  /** 线程里现在这个世界是读原件来的(同样的参数也不能拿来当新版的世界用,反过来也一样) */
  const loadedFrozen = useRef(false);
  /** 等原件的这一会儿要发的生成请求(读不出来就照它生成) */
  const genReq = useRef<WorkerRequest | null>(null);
  /** 刚另存的新版:打开它以后提示"已另存为…"(from = 原来那一份的名字) */
  const savedCopy = useRef<{ id: string; from: string; more: string[] } | null>(null);
  /**
   * 打开世界时还没核对的改名:地图上先出来的历史还没带上存档里的干预等(要在后台重推),改名的人物这时还没长出来,
   * 等重推完按推好的历史再核对(applyResim);对不上的用 show 补进打开时那条提示。terrain = 打开时的地形(改了地形就作废)
   */
  const renameCheck = useRef<{ id: string; terrain: readonly TerrainOp[]; show: (line: string) => void } | null>(null);
  // ---- 阶段 4 干预:带着干预在后台重推文明 ----
  /** 最近一次请求的文明是带着哪些干预推的(生成新世界时 = 没有) */
  const civEdits = useRef<readonly Intervention[]>(EMPTY_EDITS.interventions);
  /**
   * 地形大事:最近一次请求的文明带着哪些(civUps)、最近一次生成新世界时带着哪些(genUps)、地图上现在这份历史带着哪些(rawUps)。
   * 重推回来的和现在这份带着一样的大事,州才能沿用(地理没变)
   */
  const civUps = useRef<readonly Upheaval[] | undefined>(undefined);
  const genUps = useRef<readonly Upheaval[] | undefined>(undefined);
  /** 最近一次请求的文明是按哪种地名风格起名的(自动 = undefined) */
  const civNames = useRef<NameMix | undefined>(undefined);
  /** 最近一次请求的文明推到第几年(3000 = undefined) */
  const civYears = useRef<number | undefined>(undefined);
  /**
   * 再推 N 年(ExtendYears.tsx):正在推的这一次(第几次、从第 from 年推到第 to 年;没在推 = null)、第几次了;
   * 推完以后提示条上「撤销」要换回去的那一份(推之前的历史 before、推好的 after;提示条收起就放掉)
   */
  const extendRef = useRef<{ xid: number; from: number; to: number; t0: number; endYear: number | undefined } | null>(null);
  const extendSeq = useRef(0);
  /**
   * 照大纲推演(概览「大纲」页、侧栏「大纲」一组):正在推的这一次(第几次、推的那一份大纲、作者自己的干预;没在推 = null)、第几次了。
   * 推的时候改了大纲(界面先叫停)、下了别的干预(线程看到重推请求就不推了):推好的不换上
   */
  const outlineRef = useRef<{ oid: number; plots: Plot[]; own: Intervention[]; marks: string; characters: string; t0: number } | null>(null);
  const outlineSeq = useRef(0);
  /** 照大纲推演收起(推完、停下、被顶掉):进度和提示条一起收 */
  const endOutline = () => {
    outlineRef.current = null;
    setOutlineRun(null);
    clearToast('outline');
  };
  const extendUndo = useRef<{ before: Civ; after: Civ; from: number; endYear: number | undefined; timer: number } | null>(null);
  /** 地图上正看着助手的"先看看"(还没执行的历史):这时不再推(推的是底下真的那个世界) */
  const previewOn = useRef(false);
  previewOn.current = !!previewRaw;
  /** 最近一次请求的文明带的拓荒、起源(默认 = undefined) */
  const civSetup = useRef<CivSetup | undefined>(undefined);
  /**
   * 逐年推演:地图上这份历史(或正在推的那一份)推到的进度(没在逐年推演 = undefined)。一步走完换成新的进度时
   * 修改里的进度跟着换,对得上就不重推
   */
  const civPlay = useRef<PlayState | undefined>(undefined);
  /** 逐年推演的世界推好以后要不要马上往下走(刚点了「开始演绎」= true;从我的世界打开的停在"现在") */
  const stepAuto = useRef(false);
  /**
   * 刚从某一年重新演绎、正按新的进度推到那一年(界面已经换成停在那一年):推好以后不再从头进逐年推演(停着等「接着演绎」,
   * 推的时候点了播放的接着走),顶上提示"已回到第 N 年"
   */
  const rewindNote = useRef<{ year: number } | null>(null);
  /**
   * 正在切到别的一支(按那一支的进度从第 0 年重推):推好以后照常进逐年推演、停在那一支的"现在",
   * 顶上提示"已切到某一支"带「切回」原来那支。from = 原来那支的编号,year = 切到的那一支走到的那年
   */
  const switchNote = useRef<SwitchNote | null>(null);
  /** 下一次重推时顶上提示条换成这一句(切支线时写切到哪一支);用一次就清掉 */
  const resimText = useRef<string | null>(null);
  /** 刚创建的世界要接着往后推:推完再从第 0 年放一遍历史(true = 要放) */
  const storyAfterYears = useRef<boolean | null>(null);
  const rawUps = useRef<readonly Upheaval[] | undefined>(undefined);
  /** 读档 / 自动恢复套上的地形大事(按它重推完不提示) */
  const restoredUps = useRef<readonly Upheaval[] | undefined | null>(null);
  /** 第几次重推(只认最新的一次);这次重推从哪一年起变、什么时候发出去的 */
  const resimSeq = useRef(0);
  /** 读档 / 自动恢复套上的干预列表(按它重推完不提示"已生效"、不打断自动播放) */
  const restoredIv = useRef<readonly Intervention[] | null>(null);
  const resimInfo = useRef<{
    seq: number;
    year: number;
    t0: number;
    workerMs?: number;
    arrived?: number;
    /** 这次重推是新加了一条干预 / 撤销了一条(推完在顶部提示"…,已从 N 年起重新推演""已撤销") */
    added?: Intervention;
    removed?: Intervention;
    /** 这次重推是待推演的单子一次加了几条(干预、地形大事;推完提示"N 条命令已生效",撤销一次撤掉整批) */
    batch?: { ivs: Intervention[]; ups: Upheaval[] };
    /** 这次重推是改 / 删人物时他的即位跟着改了(推完提示"林小满的即位跟着改了；已从 N 年起重新推演";删人物的带撤销) */
    crown?: CrownResimNote;
    /** 这次重推是新加了一件地形大事 / 撤销了一件 */
    upAdded?: Upheaval;
    upRemoved?: Upheaval;
    left?: number;
    /** 读档 / 自动恢复套上的干预:推完不提示、不打断自动播放 */
    quiet?: boolean;
    /** 这次重推是一次 AI 改写 / 撤销改写(推完说"已按你说的改写",带撤销) */
    note?: RewriteNote;
    /** 这次只换了推演年数(刚创建的世界接着往后推) */
    years?: boolean;
  } | null>(null);
  /** 正在重推:从哪一年起变、推到哪一年(进度提示条上写) */
  const [resim, setResim] = useState<{ year: number; end?: number; text?: string } | null>(null);
  /** 正在按新的干预重推历史(缩略图等推完再截) */
  const resimRef = useRef(false);
  resimRef.current = !!resim;
  const rawRef = useRef<Civ | null>(null);
  rawRef.current = rawCiv;
  /** 当前这个世界(编号 reqId.current)的参数;回放时带给线程,线程重开过也能按参数重算 */
  const genParams = useRef<WorldParams | null>(null);
  // ---- 阶段 4 改地形:世界 = 参数 + 地形修改 ----
  /** 最近一次请求的世界带着哪些地形修改(回放、重推时带给线程) */
  const genTerrain = useRef<readonly TerrainOp[]>(EMPTY_EDITS.terrain);
  /** 最近一次请求的世界照着哪张草图(没画 = undefined;回放、重推时带给线程) */
  const genSketch = useRef<SketchEdit | undefined>(undefined);
  /** 换了新世界、还没套上它的修改(自动恢复 / 读档)之前:这时的修改不属于这个世界,不按它重新生成 */
  const fresh = useRef(false);
  /** 正在进行的"按新地形重新生成"(编号 = 那次生成的请求编号);t0 = 发出去的时刻 */
  const regenRef = useRef<{
    id: number;
    t0: number;
    terrain: readonly TerrainOp[];
    sketch?: SketchEdit;
    workerMs?: number;
    arrived?: number;
    /** 线程交回来的时刻(毫秒,从发出去算起)、线程里铺像素用了多久、按块换上的备料统计(冒烟检查、测速用) */
    got?: number;
    rasterMs?: number;
    patch?: PatchStats;
    /** 地形图换上以后的下一帧(从发出去算起,毫秒) */
    shown?: number;
  } | null>(null);
  /** 地图上那张整图(baseRef)是哪个世界的(线程的 baseKey;编辑地形时线程按它判断能不能只交回变了的那块) */
  const baseKeyRef = useRef<string | null>(null);
  /** 最近一次发出去的生成请求(按块重铺对不上时按整张重新要) */
  const genSent = useRef<WorkerRequest | null>(null);
  /** 编辑地形后在后台按投影画好的整张地形图(弯边投影时换上地图直接贴它,见 ui/terrainPatch.ts) */
  const preProj = useRef<PreProjected | null>(null);
  /** 正在进行的"按新地形重新生成"是一次 AI 改写 / 撤销改写(生成完说"已按你说的改写",带撤销) */
  const regenNote = useRef<RewriteNote | null>(null);
  /**
   * 编辑地形时不起名:新建世界里编辑地形(照手绘图新建是第 2 步「用笔修改」),涂了第一笔起到收起编辑地形(点「完成」「保存地图」「打造文明 ›」,
   * 照手绘图的去第 3 步、点「创建世界」)为止,按新地形重新生成只换地形、不推历史(线程的 skipCiv),地图上不标地名;
   * 收起时补推一次历史、起地名(civOnly,和一起推的逐字节一样)。null = 不在这一段里;tip = 这一段里提示过"地名等点「完成」以后再起"了
   */
  const namesHold = useRef<{ tip: boolean } | null>(null);
  /** 同 namesHold(画面用:这一段里地图上不标地名) */
  const [namesHeld, setNamesHeld] = useState(false);
  /** 地图上这个世界还没推历史(编辑地形时生成的,rawCiv = null),要补推 */
  const civLater = useRef(false);
  /** 正在补推历史、起地名:nid = 第几次补推(线程交回的只认这一次)、t0 = 发出去的时刻 */
  const naming = useRef<{ nid: number; t0: number } | null>(null);
  const namingSeq = useRef(0);
  /** 补推的进度(提示条"正在起地名"的进度条;null = 没在补推) */
  const [namingPct, setNamingPct] = useState<number | null>(null);
  /** 上一次推历史用了多久(毫秒;估补推的进度用) */
  const civMsLast = useRef<number | null>(null);
  /**
   * 地图先交的生成(新建中的世界,mapFirst):先到的世界、地图换上了没有、地图换上之前先到了的历史(done)。
   * mapEarly = 地图换上了、历史还在推(新建界面的星球这时就换上新的一颗;按钮照旧等历史)
   */
  const mapFirst = useRef<{ id: number; world: World; shown: boolean; done: Extract<WorkerResponse, { type: 'done' }> | null } | null>(null);
  const [mapEarly, setMapEarly] = useState(false);
  /** 补推完、地名刚换上(那一次的编号;淡入完 = 0):地图上的字淡入 */
  const [namesIn, setNamesIn] = useState(0);
  /** 这次"已按新地形重新生成"多写一行"地名等点「完成」以后再起"(每段编辑只在第一笔换上后写) */
  const holdTip = useRef(false);
  /** 编辑地形时不起名的这一段、要补推的历史、正在补推的都不算了(换了世界) */
  const endNamesHold = () => {
    namesHold.current = null;
    setNamesHeld(false);
    civLater.current = false;
    naming.current = null;
    setNamingPct(null);
  };
  /** 地图上现在这个世界带着的地形修改(覆盖层据此标出还在生成的那几处) */
  const [shownTerrain, setShownTerrain] = useState<readonly TerrainOp[]>(EMPTY_EDITS.terrain);
  const [shownSketch, setShownSketch] = useState<SketchEdit | undefined>(undefined);
  const [terrainStatus, setTerrainStatus] = useState<TerrainStatus>({ busy: false });
  const terrainTool = useTerrainTool();
  // 导入图片时地图上只看图(地名先藏起来)
  const importing = useImportOn();
  const sourceView = useSourceView();
  // 手机:改地形、回放世界形成都要看地图 —— 拉到顶的世界卡片先收起来(两样都是从卡片里的"地形"那一组点开的)
  useEffect(() => {
    if (terrainTool.on || replayOn) setWorldSheet('peek');
  }, [terrainTool.on, replayOn]);
  // 点了一条大事(卡片里的"最近大事"、编年史):时间轴跳过去、地图上标出来 —— 世界卡片也先收起
  const chronPick = useChroniclePick();
  useEffect(() => {
    if (chronPick.entry) setWorldSheet('peek');
  }, [chronPick]);
  // 3D 地球仪(网址 proj=globe,旧链接的 view=globe 也认 / 地图右下角的按钮):主图藏起来,同一套时间轴、详情面板、选中逻辑
  const globeOn = useGlobeOn();
  /** 地球仪第一帧画好了(打开时它先在后台备贴图,这之前平面地图照旧显示着) */
  const [globeShown, setGlobeShown] = useState(false);
  if (!globeOn && globeShown) setGlobeShown(false);
  /** 等值线画不画:新建世界时、地球仪上不画 */
  const contourOn = !!contourKind && !draft && !globeOn;
  /** 地理图:左上角放海拔色标(地球仪上不放) */
  const atlasOn = mapBase === 'geo' && !globeOn;
  // 等值线、经纬网的墨色:白模、地理图是浅底,和数据底图一样用深色线
  const contourStyle = mapBase === 'blank' || mapBase === 'geo' ? 'data' : style;
  const contourInkNow = contourKind ? contourInk(contourKind, contourStyle, baseDark(mapBase)).line : undefined;
  const globeApi = useRef<GlobeApi | null>(null);
  /** 世界坐标 → 屏幕坐标(地图上的事件标签、截图脚本用;下面 __wfWorldToClient 那里定义) */
  const worldToClient = useRef<WorldToClient | null>(null);
  /** 地球仪上的世界坐标 → 屏幕坐标(转到背面 = null),地球仪打开时给事件标签用 */
  const globeToClient = useRef<WorldToClient>((wx, wy) => globeApi.current?.worldToClient(wx, wy) ?? null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  /** 最近生成完的世界(打开的世界就是正在看的这一个时,不用重新生成) */
  const lastReady = useRef<{ world: World; civ: Civ } | null>(null);
  /** 打不开的分享链接(世界还在生成时解开的):生成完再提示 */
  const shareErr = useRef<string | null>(null);
  /** 世界生成完的处理(存档:自动恢复 / 读档套修改);线程回调里经 ref 调,拿到的总是最新的 */
  const readyRef = useRef<(world: World, civ: Civ) => void>(() => {});
  const dataRef = useRef(data);
  dataRef.current = data;
  /** 生成出来的世界(地形大事以前的;线程回调里用) */
  const baseRef = useRef(baseData);
  /** 最近一次编辑地形(按新地形重新生成)换上的那一份(就是 baseRef 那个对象;之后换了别的世界 = null):样式缩略图先留着旧的 */
  const editedRef = useRef<object | null>(null);
  const eraMapsRef = useRef(eraMaps);
  eraMapsRef.current = eraMaps;
  /** 弯边投影:当前投影 + 中心放进地图平面(等距圆柱 = null,照原来的办法画) */
  const mp = useMemo(() => (data ? curvedProj(projection, mapCenter, data.world.width, data.world.height) : null), [data, projection, mapCenter]);
  const mpRef = useRef<MapProj | null>(mp);
  mpRef.current = mp;
  /** 地图现在怎么画(编辑地形按块换上时,线程回调里看这一份决定重画哪种像素层) */
  const drawView = useRef<PatchView>({ style, look: paintedLook, mp });
  drawView.current = { style, look: paintedLook, mp };
  /** 地图现在这种底图在缓存里的键(baseKeyOf):整张交回来的新主图换上之前,先在后台把这一张备好 */
  const drawKey = useRef(baseKeyOf(style, layer, paintedLook));
  drawKey.current = baseKeyOf(style, layer, paintedLook);
  // 换段:要换过去的那一段的整张底图(这种底图)、写实 / 卫星画风整张图上的河、文明层第一次要画的,在后台分小步备好,
  // 备好了 eraK 再换过去(和换上那一下一口气整张画逐像素相同)。又要换到别的段(接着拖时间轴、又到了补丁)就顶掉重备
  useEffect(() => {
    if (!baseData || eraK === eraNext) return;
    const k = eraNext;
    const raw = previewRaw ?? rawCiv;
    const view = drawView.current;
    const key = warmKey;
    let d: { world: World; raster: Raster } | null = null;
    const steps: WorkStep[] = [
      // 拼那一段的主图(补丁贴到原主图的复制品上)
      () => void (d = eraData(baseData, eraMaps, eraPatches.current, k)),
      later(() => [
        ...thumbPrepSteps(key, d!.world, d!.raster),
        ...(view.style === 'realistic' ? realisticRiverSteps(d!.world, d!.raster, view.look) : []),
        ...(raw ? civOpenSteps({ world: d!.world, raster: d!.raster, civ: civAtEra(raw, k), style: view.style as Style, mp: view.mp }) : []),
      ]),
    ];
    // 备料出了错:不再等,换过去(换上时照常当场画),错误照常报出去
    let failed = false;
    const guarded = steps.map((s): WorkStep => (deadline) => {
      if (failed) return;
      try {
        return s(deadline);
      } catch (e) {
        failed = true;
        setTimeout(() => {
          throw e;
        });
      }
    });
    submitDetailJob(
      ERA_WARM_JOB,
      guarded,
      () => {
        eraWarm.current = { data: d ?? eraData(baseData, eraMaps, eraPatches.current, k), key };
        setWarmVer((n) => n + 1);
      },
      { alone: true },
    );
    return () => cancelDetailJob(ERA_WARM_JOB);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- patchVer:补丁变了要换的那一段的主图跟着变;previewRaw / rawCiv 只在换段时取
  }, [baseData, eraMaps, patchVer, eraK, eraNext, warmKey]);

  // ---- 后台线程 ----
  // 线程一次只能算一个世界。连续改参数时,与其排队把每个中间世界都算完,
  // 不如直接终止还在忙的旧线程、另开一个(启动只要几十毫秒),只算最后一次。
  // 回放帧、重推文明这些短活不打断线程,排在后面(打断了,线程手上的世界就没了,得按参数重新生成,反而更慢)。
  // 编辑地形时只换地形的生成(skipCiv)也不关线程:线程自己半路放下它(见 worker.ts 文件头),记着的网格、整图留给新的一笔。
  /** 线程回报的扩张节拍(改过地形的世界推文明要用):下次生成、重推时带回去,线程被重开过也不用多生成一遍原来的地形 */
  const tempoNote = useRef<TempoNote | null>(null);
  const idleWorker = useCallback((abort: boolean) => {
    if (abort && workerRef.current && busyRef.current > softRef.current.size) {
      workerRef.current.terminate();
      workerRef.current = null;
      // 线程上排着的试推演(助手)一起作废
      for (const t of trials.current.values()) t.reject(new Error('世界换了,试推演作废'));
      trials.current.clear();
    }
    if (!workerRef.current) {
      const w = new Worker(WORKER_URL, { type: 'module' });
      dropChronicleParts();
      civParts.drop();
      w.onerror = (e) => {
        if (workerRef.current === w) recordWorkerError(e, '生成世界的线程');
      };
      w.onmessage = (e: MessageEvent<WorkerResponse>) => {
        const m = e.data;
        if (workerRef.current !== w) return; // 已被换掉的线程
        // 交历史之前先交的几段历史(条数多的列表,src/civParts.ts):收着;交历史的那条到了先拼回去,别处拿到的都是整份
        if (m.type === 'civPart') return void civParts.take(m);
        if ('split' in m && m.split) civParts.join(m.civ!, m.split);
        // 主图补丁、原件是后台自己排的活,不算一件回音(再推的进度、先交的编年史、先交的地图也不算:推完 / 停下才算)
        if (m.type !== 'progress' && m.type !== 'eraPatch' && m.type !== 'snapshot' && m.type !== 'extendProgress' && m.type !== 'outlineProgress' && m.type !== 'chronicle' && m.type !== 'map') {
          busyRef.current = Math.max(0, busyRef.current - 1);
          if (!busyRef.current) {
            workLabel.current = null;
            diagBeat();
          }
          if (m.type === 'done' || m.type === 'aborted') softRef.current.delete(m.id);
        }
        // 半路放下的生成(被新的一笔顶掉了):只是一声回音
        if (m.type === 'aborted') return;
        if ((m.type === 'done' || m.type === 'civ' || m.type === 'trial') && m.tempo) tempoNote.current = m.tempo;
        if (m.type === 'trial') {
          // 试推演(助手):交给等着它的那一次;世界换了的话助手那边已经停下,结果没人要
          const t = trials.current.get(m.tid);
          trials.current.delete(m.tid);
          t?.resolve(m.civ);
          return;
        }
        if (m.id !== reqId.current) return; // 过时的请求(上一个世界的)
        // 交历史之前先交的编年史:收着,交历史的那条到了一起记下(换上时不在主线程上整段重算)
        if (m.type === 'chronicle') return void takeChroniclePart(m);
        if (m.type === 'done' || m.type === 'civ' || m.type === 'civOnly' || m.type === 'turn' || m.type === 'extended' || m.type === 'outlined') adoptChronicle(m.civ, m.chron);
        if (m.type === 'eraPatch') {
          // 一段的主图补丁:记下,地图那一段换上(eras.ts);最多留 PATCH_KEEP 块,先丢最早的(现在这份历史要用的不丢;
          // 丢了的以后又要用,下一次推演时线程看 have 里没有会重新铺)
          const map = eraPatches.current;
          const k = patchKey(m.prev, m.key);
          map.delete(k);
          map.set(k, m.patch);
          const cur = eraMapsRef.current;
          const keep = new Set(cur ? cur.keys.map((key, i) => patchKey(i ? cur.keys[i - 1] : cur.baseKey, key)) : []);
          for (const old of [...map.keys()]) if (map.size > PATCH_KEEP && !keep.has(old)) map.delete(old);
          setPatchVer((v) => v + 1);
          return;
        }
        if (m.type === 'upPreview') return void takeUpPreview(m.pid, m.preview, m.water, m.ms);
        // 原件读不出来:按现在的规则生成(提示条上说一句)
        if (m.type === 'loadFailed') {
          const req = genReq.current;
          frozenBroken.current = frozenLoad.current?.id ?? null;
          frozenLoad.current = genReq.current = null;
          loadedFrozen.current = false;
          civEdits.current = EMPTY_EDITS.interventions;
          civUps.current = genUps.current = undefined;
          if (req) sendRef.current(req);
          return;
        }
        // 这次生成 / 重推的原件:对得上存着的存档就存进浏览器(resultStore.ts)
        if (m.type === 'snapshot') {
          void offerSnapshot(m.snapshot);
          void noteMapSum(m.snapshot);
          return;
        }
        /** 历史到了(和地图一起到的;地图先交了的,是地图换上以后):记下速度,换上历史,套上要打开的那个世界的修改 */
        const takeCiv = (d: { id: number; civ: Civ | null; ms: number; genMs: number; civMs?: number; reused?: true }, world: World) => {
          // 读原件来的、只算了后一半的(编辑地形接着上一次)不算生成速度
          if (!frozenLoad.current && !d.reused) noteGenSpeed(world.params.cells, d.genMs, d.ms);
          // 推文明那一步用了多久:「再推」的弹层拿它估这台电脑再推几年要多久
          if (d.civMs && d.civ) {
            noteExtendSpeed(0, d.civ.endYear, d.civMs);
            civMsLast.current = d.civMs;
          }
          setRawCiv(d.civ);
          // 编辑地形时生成的(没推历史):收起编辑地形时补推
          civLater.current = !d.civ;
          setProgress(null);
          setMapEarly(false);
          const rg = regenRef.current;
          if (rg && rg.id === d.id) terrainDoneRef.current(world, d.civ, d.ms);
          else {
            fresh.current = false;
            if (d.civ) readyRef.current(world, d.civ);
          }
        };
        /** 地图先换上了的(mapFirst)历史到了:接上;检查脚本看的"世界齐了"这时才算(地图画好时没算,见地图那一层的 __wf) */
        const civAfterMap = (d: Extract<WorkerResponse, { type: 'done' }>, world: World) => {
          mapFirst.current = null;
          takeCiv(d, world);
          const w = (window as unknown as { __wf?: { ready: boolean } }).__wf;
          if (w) w.ready = true;
        };
        if (m.type === 'progress') setProgress((s) => ({ stage: m.stage, pct: m.pct, regen: regenRef.current?.id === m.id, seed: s?.seed }));
        else if (m.type === 'done' && m.mapSent) {
          // 地图先交了的(mapFirst):地图换上了就接上历史;还在备地图的,换上时再接
          const mf = mapFirst.current;
          if (!mf || mf.id !== m.id) return;
          if (!mf.shown) return void (mf.done = m);
          civAfterMap(m, mf.world);
        } else if (m.type === 'done' || m.type === 'map') {
          // map = 地图先交(还没推文明):照常备好、换上地图,历史等随后的 done
          const early = m.type === 'map';
          const civ = early ? null : m.civ;
          if (early) mapFirst.current = { id: m.id, world: m.world, shown: false, done: null };
          const rg0 = regenRef.current;
          if (rg0 && rg0.id === m.id) {
            rg0.got = performance.now() - rg0.t0;
            rg0.rasterMs = m.rasterMs;
          }
          // 各段的世界(有地形大事的;换上时 setEraMaps 用同一份:备好的那一段的世界、拼好的主图对得上)
          const maps = m.eras ? eraMapsOf(m.world, m.baseKey, m.eras) : null;
          /** 换上时画第几段(打开世界时备好了的那一段;按块换上的 = null,换上时照常定) */
          let openK: number | null = null;
          const finish = (raster: Raster) => {
            // 换了世界:别的世界的各段主图补丁都作废(这个世界的几段在备地图的时候可能已经先到了,留着)
            const chain = new Set((m.eras ?? []).map((e, i, a) => patchKey(i ? a[i - 1].key : m.baseKey, e.key)));
            for (const k of [...eraPatches.current.keys()]) if (!chain.has(k)) eraPatches.current.delete(k);
            dropComposed(raster);
            // 换了主图:各画风缓存里别的主图的像素层连旧主图现在就放掉,不等下次画那种画风(按块换上的留着它是从哪张改来的;
            // 打开时拼好、备好了的那一段的主图也留着)
            const keepBases = [raster, patchSourceOf(raster)?.r0, ...composedOf(raster)];
            dropRealisticBasesExcept(keepBases);
            dropFantasyBasesExcept(keepBases);
            baseRef.current = { world: m.world, raster };
            baseKeyRef.current = m.baseKey;
            editedRef.current = regenRef.current?.id === m.id ? baseRef.current : null;
            setData(baseRef.current);
            setEraMaps(maps);
            // 备好的是第几段:换上以后时间轴要的那一段要是还没备(备的时候又到了补丁),先画备好的这段,另一段在后台备好再换(eraK)
            eraAt.current = openK === null ? null : { maps, base: baseRef.current, k: openK };
            eraWarm.current = null;
            rawUps.current = genUps.current;
            if (!early) return takeCiv(m, m.world);
            // 地图先换上:上一个世界的历史不能留在新地图上;提示条照旧("文明"那一步),历史到了才收
            setRawCiv(null);
            civLater.current = false;
            setMapEarly(true);
            const mf = mapFirst.current;
            if (!mf || mf.id !== m.id) return;
            mf.shown = true;
            if (mf.done) civAfterMap(mf.done, mf.world);
          };
          if (m.raster) {
            // 整张交回来的(打开世界、换世界、刷新、新建……):现在这种底图的整张图先分小步在后台备好再换上,
            // 不在换上那一下在主线程上一口气画半秒到几秒;备的时候加载画面照旧
            const raster = m.raster;
            // 线程算好的手绘符号规划(推了文明的才带)
            if (m.plan) adoptPlan(m.world, m.plan);
            // 线程画好的写实像素层(新建中的世界):下面备这种底图、新建界面的星球要那一张时直接贴上
            if (m.type === 'map' && m.painted) takeRealisticPainted(raster, m.painted);
            // 换上时画的那一段:有地形大事、时间轴在大事以后、那一段的主图补丁已经在手里的,是拼好的那张(拼也放在后台的一步里)。
            // 那一段的整张底图、写实 / 卫星画风整张图上的河(矢量,换上时描)、文明层第一次要画的,都一起备好,和地图一起换上
            const view = drawView.current;
            const civ0 = civ;
            const k = civ0 ? eraShown(maps, eraPatches.current, eraIndex(civ0, getCivTime().year)) : 0;
            openK = k;
            const base = { world: m.world, raster };
            const stepsFor = (d: { world: World; raster: Raster }) => [
              ...thumbPrepSteps(drawKey.current, d.world, d.raster),
              ...(view.style === 'realistic' ? realisticRiverSteps(d.world, d.raster, view.look) : []),
              ...(civ0 ? civOpenSteps({ world: d.world, raster: d.raster, civ: civAtEra(civ0, k), style: view.style as Style, mp: view.mp }) : []),
            ];
            let shown = base;
            const prep = k > 0 ? [() => void (shown = eraData(base, maps, eraPatches.current, k)), later(() => stepsFor(shown))] : stepsFor(base);
            startTerrainFull({ world: m.world, raster, view, prep, shown: () => shown }, (st, pre) => {
              if (m.id !== reqId.current) return;
              (window as unknown as { __wfOpenPrep: unknown }).__wfOpenPrep = st;
              preProj.current = pre;
              finish(raster);
            });
          } else {
            // 编辑地形按块重铺的:只带回变了的那块,贴到地图上那张整图上;按块重画的像素层分小步备好再一次换上
            const b = baseRef.current;
            if (!b || baseKeyRef.current !== m.from) {
              // 地图上那张不是线程比的那张(不该发生):这次按整张重新要一遍
              const req = genSent.current;
              if (req?.type === 'generate' && req.id === m.id) sendRef.current({ ...req, from: undefined });
              return;
            }
            adoptPlan(m.world, m.plan);
            startTerrainPatch({ w0: b.world, r0: b.raster, w1: m.world, patch: m.patch, view: drawView.current }, (r1, st, pre) => {
              if (m.id !== reqId.current) return;
              const rg = regenRef.current;
              if (rg && rg.id === m.id) rg.patch = st;
              preProj.current = pre;
              finish(r1);
              // 换上了:线程不用再留着怎么改回上一张(还没换上就又涂了一笔时,线程照上一张接着按块重铺要用)
              workerRef.current?.postMessage({ type: 'shown', id: m.id, key: m.baseKey } satisfies WorkerRequest);
            });
          }
        } else if (m.type === 'history') {
          setReplay({ w: m.w, h: m.h, frames: m.frames, mya: m.mya, idx: 0 });
        } else if (m.type === 'civ') {
          if (m.seq !== resimSeq.current) return; // 又下了新的干预,等最新的那一次
          applyResimRef.current(m.civ, m.ms, m.eras, m.baseKey);
        } else if (m.type === 'civOnly') {
          namesDoneRef.current(m.nid, m.civ, m.civMs);
        } else if (m.type === 'turn') {
          applyTurnRef.current(m.civ, m.play, m.rejected, m.eras, m.baseKey);
        } else if (m.type === 'extendProgress') {
          if (extendRef.current?.xid === m.xid) extendProgress(m.xid, m.year, m.pct);
        } else if (m.type === 'extended') {
          applyExtendedRef.current(m.xid, m.civ, m.to, m.ms, m.eras, m.baseKey);
        } else if (m.type === 'extendStopped') {
          if (extendRef.current?.xid === m.xid) {
            extendRef.current = null;
            setExtendBusy(null);
          }
        } else if (m.type === 'outlineProgress') {
          outlineProgressRef.current(m.oid, m.done, m.total, m.review, m.at);
        } else if (m.type === 'outlined') {
          applyOutlinedRef.current(m.oid, m.civ, m.interventions, m.review, m.ms, m.eras, m.baseKey);
        } else if (m.type === 'outlineStopped') {
          if (outlineRef.current?.oid === m.oid) endOutline();
        }
      };
      workerRef.current = w;
      busyRef.current = 0;
      softRef.current.clear();
    }
    return workerRef.current;
  }, []);
  const send = useCallback(
    (req: WorkerRequest) => {
      // 换了世界、读档、重推、逐年推演走一步:正在再推的那一次线程会自己停下(推了一半的不要),界面上跟着收起
      if (extendRef.current && (req.type === 'generate' || req.type === 'load' || req.type === 'resim' || req.type === 'turn')) {
        extendRef.current = null;
        setExtendBusy(null);
      }
      // 照大纲推演同样:线程看到排着的新请求就不推了(交回 outlineStopped),界面上先收起
      if (outlineRef.current && (req.type === 'generate' || req.type === 'load' || req.type === 'resim' || req.type === 'turn' || req.type === 'extend')) endOutline();
      const w = idleWorker(req.type === 'generate' || req.type === 'load');
      if (req.type === 'generate') genSent.current = req;
      if (req.type === 'generate' && req.skipCiv) softRef.current.add(req.id);
      // 又要了一个新世界:还在后台备着换上的那一次已经过时了(线程交回的旧结果本来也不认)
      if (req.type === 'generate' || req.type === 'load') {
        cancelTerrainPatch();
        dropPreparedRivers();
      }
      busyRef.current++;
      // 问题记录:意外关闭时记下线程在忙什么
      workLabel.current = WORK_LABEL[req.type] ?? workLabel.current;
      diagBeat();
      // 交回历史的请求带上现在的改名:线程先交套上它的编年史(打开世界时那两种自己带着存档里的改名;试推演不换上,不用)
      const named = (req.type === 'generate' || req.type === 'civOnly' || req.type === 'resim' || req.type === 'turn' || req.type === 'extend') && !req.renames ? { ...req, renames: getEdits().names } : req;
      w.postMessage(named.type === 'history' || named.type === 'upPreview' || !tempoNote.current ? named : { ...named, tempo: tempoNote.current });
    },
    [idleWorker],
  );
  const sendRef = useRef(send);
  sendRef.current = send;
  // 助手的试推演:和重推一样交给线程(排在别的活后面),结果单独交回、不换上去;州和宜居度沿用现在这份
  useEffect(() => {
    setTrialRunner(
      (interventions, signal) =>
        new Promise<Civ>((resolve, reject) => {
          const p = genParams.current;
          if (!p || !rawRef.current) return reject(new Error('世界还没生成好'));
          // 逐年推演只看得到"现在"以前:不在后台试推演以后会怎样
          if (getStepwise().on || cleanPlay(getEdits().play)) return reject(new Error('逐年推演里不试推演：以后的事还没发生。想试，先存回推演模式'));
          const tid = ++trialSeq.current;
          const onAbort = () => {
            trials.current.delete(tid);
            reject(new Error('已停下'));
          };
          if (signal?.aborted) return onAbort();
          signal?.addEventListener('abort', onAbort, { once: true });
          const ups = civUps.current;
          trials.current.set(tid, {
            resolve: (next) => {
              signal?.removeEventListener('abort', onAbort);
              const old = rawRef.current;
              resolve(old ? reuseRegions(old, next, sameUpheavals(ups, rawUps.current)) : next);
            },
            reject: (e) => {
              signal?.removeEventListener('abort', onAbort);
              reject(e);
            },
          });
          send({ type: 'trial', id: reqId.current, tid, params: p, terrain: [...genTerrain.current], sketch: genSketch.current, interventions: [...interventions], ...upsOpt(ups), ...namesOpt(civNames.current), ...yearsOpt(civYears.current), ...setupOpt(civSetup.current) });
        }),
    );
    return () => setTrialRunner(null);
  }, [send]);
  // 逐年推演:算一步(worker 的 turn)、从推演模式某一年开始、存回推演模式、重新演绎、切支线
  useEffect(() => {
    /**
     * 重新演绎、切支线:正在算的那一步先等它算完、换上(或者没算成),再做 fn。这样原来那一支照它真走到的样子留下,
     * 交回来的那一步也不会落到另一支上;单子里还没交出去的干预本来就在下一步开头生效,正好是那时的"现在"。
     * 没在算 = 马上做;等的时候换了世界、不在逐年推演了 = 不做。一次只等一件(waiting 的时候两个动作都先不接)
     */
    let waiting = false;
    const afterStep = (fn: () => void) => {
      if (!getStepwise().busy) return fn();
      if (waiting) return;
      waiting = true;
      const off = subscribeStepwise(() => {
        const t = getStepwise();
        if (t.on && t.busy) return;
        off();
        waiting = false;
        if (t.on) fn();
      });
    };
    /**
     * 原来那一支要留下的样子(重新演绎、切走时):单子里还没交出去的干预(和万一还在算的那一步带走的)
     * 都当作在"现在"下的(在那一年年初生效,同存回推演模式)。没在逐年推演 = null
     */
    const keptBranch = (): WorldEdits | null => {
      const e0 = getEdits();
      const play = cleanPlay(e0.play);
      if (!play) return null;
      const later = [...(getStepwise().busy?.commands ?? []), ...getPending().flatMap((x) => (x.kind === 'iv' ? [x.v] : []))];
      const now = later.map((v) => ({ ...v, from: play.year }) as Intervention);
      return now.length ? { ...e0, play: issueCommands(play, now).play } : e0;
    };
    /** 单子里还没交出去的干预已经记进原来那一支:从单子里拿掉 */
    const dropPending = () => {
      for (const x of getPending()) if (x.kind === 'iv') removePending(x.id);
    };
    setStepwiseActions({
      turn: (years, commands) => {
        const p = genParams.current;
        const play = cleanPlay(getEdits().play);
        // 地图上这份历史得正是按现在这份进度推的(不在重推、不在生成)
        if (!p || !play || !rawRef.current || fresh.current || regenRef.current || resimInfo.current || JSON.stringify(play) !== JSON.stringify(civPlay.current ?? null)) return false;
        send({
          type: 'turn',
          id: reqId.current,
          play,
          commands,
          years,
          params: p,
          terrain: [...genTerrain.current],
          sketch: genSketch.current,
          interventions: [...civEdits.current],
          ...upsOpt(civUps.current),
          ...namesOpt(civNames.current),
          ...setupOpt(civSetup.current),
        });
        return true;
      },
      start: (year, drop, adv) => {
        const cur = currentWorld();
        if (!cur || !rawRef.current) return;
        // 推进设置只写进新的那个(原来的世界不动)
        const { advance: _old, ...rest } = getEdits();
        void _old;
        const a = cleanAdvance(adv);
        const e = startStepwise(a ? { ...rest, advance: a } : rest, year, drop);
        // 原来的世界不动:另存一个从这一年开始演绎的(名字照旧;存回推演模式时能选覆盖原来那个)
        const id = saveCurrentAs(e, cur.title || '', isStored(cur.id) ? cur.id : undefined);
        if (!id) return notify({ kind: 'error', text: '没能开始演绎', more: [storageFullWhy()] });
        stepAuto.current = true;
        openStoredRef.current(id);
      },
      saveBack: (asNew, open) => {
        const cur = currentWorld();
        const e0 = getEdits();
        const play = cleanPlay(e0.play);
        if (!cur || !play) return;
        // 正在算的那一步带走的干预、单子里还没交出去的:都当作在"现在"下的,一起存进去(在那一年年初生效;
        // 正在算的那一步还没换上来,修改里的进度还是"现在")
        const inflight = getStepwise().busy?.commands ?? [];
        const normal = saveBackEdits(e0, [...inflight, ...getPending().flatMap((x) => (x.kind === 'iv' ? [x.v] : []))]);
        if (!normal) return notify({ kind: 'error', text: '没能存回推演模式', more: ['推得太远了，普通世界最多推到第 60000 年'] });
        const origin = stepOrigin(cur.id);
        let id: string | null;
        let title: string;
        if (!asNew && origin) {
          id = overwriteWorld(origin.id, normal) ? origin.id : null;
          title = origin.title;
        } else {
          const want = `${cur.title || '未命名世界'}${SAVE_SUFFIX}`;
          title = listWorlds().some((w) => w.save.title === want) ? nextTitle(want) : want;
          id = saveCurrentAs(normal, title);
        }
        if (!id) return notify({ kind: 'error', text: '没能存回推演模式', more: [storageFullWhy()] });
        if (open) return openStoredRef.current(id);
        showToast({ id: 'step-saved', kind: 'ok', dot: true, text: `已存回推演模式「${title}」`, more: ['这个故事照样留着，在「我的世界」里随时能打开那一个'], ttl: 6000 });
      },
      rewind: (year, name) => {
        // 正在切支线:地图、时间轴上还是原来那支,修改里已经是切到的那一支,这时另开会从切到的那一支分出去
        // (切的时候问重新演绎的窗口本来就不开,见 openStepDialog);已经在等着做别的:这次不做
        if (getStepwise().switching || waiting) return;
        setCivTime({ playing: false });
        afterStep(() => {
          const e0 = keptBranch();
          const play = e0 && cleanPlay(e0.play);
          // 原来那条原样留成一支(记下它的最后一件大事),从那一年另开一支、切过去
          const r = e0 && play && rewindBranch(e0, year, name, branchNote(rawRef.current, play.year));
          if (!play || !r || !r.edits.play) return notify({ kind: 'error', text: '没能从这一年重新演绎', more: ['另开的支太多了'] });
          const T = r.edits.play.year;
          rewindNote.current = { year: T };
          dropPending();
          // 进度换成那一年年初(App 照它从第 0 年推到那一年)
          putEditsQuiet(r.edits);
          rewoundTo(playFromOf(r.edits), T);
          setCivTime({ year: T, playing: false, scrubbing: false, story: false });
        });
      },
      switchBranch: (id) => {
        const s = getStepwise();
        const all = branchList(getEdits());
        const cur = all.find((b) => b.current);
        const to = all.find((b) => b.id === id && !b.current);
        // 正在切、等着重新演绎、正在重推 / 生成(地图上的历史还不是这一支的)时不切
        if (!s.on || s.switching || waiting || resimInfo.current || regenRef.current || !cur || !to) return;
        // 那一行先转起圈来(别的行、下令先不能点),停下;正在算的那一步算完再切
        branchSwitching({ to: id, from: cur.id, ...(to.last ? { last: to.last } : {}) });
        stepAuto.current = false;
        rewindNote.current = null;
        setCivTime({ playing: false });
        afterStep(() => {
          const e0 = keptBranch();
          const play = e0 && cleanPlay(e0.play);
          const next = e0 && play && !resimInfo.current && !regenRef.current ? switchBranch(e0, id, branchNote(rawRef.current, play.year)) : null;
          if (!e0 || !next?.play) return branchSwitching(null);
          dropPending();
          const note: SwitchNote = { from: cur.id, fromRef: branchRef(cur), toRef: branchRef(to), year: next.play.year };
          // 两支走到的一模一样(另开以后原样走回了同一年):地图上这份历史就是它的,不用重推,直接换上
          if (JSON.stringify(next.play) === JSON.stringify(civPlay.current ?? null)) {
            putEditsQuiet(next);
            enterStepwise(playFromOf(next), next.play.year);
            setCivTime({ year: next.play.year, playing: false, scrubbing: false, story: false });
            return switchedToast(note);
          }
          // 地图先留着原来那支(照样能拖),在后台照那一支从第 0 年推到它走到的那一年,推完换上、停在那一年
          switchNote.current = note;
          resimText.current = `正在切到${branchRef(to)}：从头推到${spaced(yearAt(next.play.year, e0.era))}`;
          putEditsQuiet(next);
        });
      },
    });
    return () => setStepwiseActions(null);
  }, [send]);
  // 地形大事的"会怎么样":交给线程照"那一年的地形 + 这几笔"生成一遍。那一年的地形按卡片给的大事算(修改里现在的,和预览的键同一份):
  // 刚加了一件、重推还没完时,线程先推完那一次才轮到这次预览,结果回来时地图上已经是新的历史
  useEffect(() => {
    setUpRunner((pid, year, ops, ups) => {
      const p = genParams.current;
      if (!p) return;
      send({ type: 'upPreview', id: reqId.current, pid, params: p, terrain: [...genTerrain.current], sketch: genSketch.current, ...upsOpt(ups), ...(civSetup.current?.civSeed !== undefined ? { civSeed: civSetup.current.civSeed } : {}), year, ops: [...ops] });
    });
    return () => setUpRunner(null);
  }, [send]);

  /**
   * 历史换了一份(重推完、在地图上看试推演 / 回到现在):选中的东西、编年史和人物页的国家筛选按稳定键换成新历史里的编号(指不到就取消)。
   * 选中的地方(山海河湖)在下面跟着地图上的地名表换
   */
  const remapSelection = (old: Civ, civ: Civ) => {
    const { sel } = getSelection();
    if (sel) {
      const key =
        sel.kind === 'polity' && old.polities[sel.id]
          ? polityKey(old, sel.id)
          : sel.kind === 'settlement' && old.settlements[sel.id]
            ? settlementKey(old, sel.id)
            : sel.kind === 'faith' && old.religion?.faiths[sel.id]
              ? faithKey(old, sel.id)
              : sel.kind === 'treaty'
                ? treatyKey(old, sel.id) || null
                : null;
      if (key) {
        const r = resolveKey(civ, key);
        if (r && r.kind === sel.kind) setSelection({ kind: sel.kind, id: r.id } as MapSelection);
        else clearSelection();
      } else if (sel.kind === 'person') {
        // 人物:同一国、同名、同年生的还在就还选着他(重推后历史变了,多半找不到了)
        const id = old.people?.[sel.id] ? resolvePersonKey(civ, personKey(old, sel.id)) : -1;
        if (id >= 0) setSelection({ kind: 'person', id });
        else clearSelection();
      }
    }
    const cp = getChronicle().polity;
    if (cp !== null) {
      const r = old.polities[cp] ? resolveKey(civ, polityKey(old, cp)) : null;
      setChronicle({ polity: r && r.kind === 'polity' ? r.id : null });
    }
    const pp = getPeople().polity;
    if (pp !== null) {
      const r = old.polities[pp] ? resolveKey(civ, polityKey(old, pp)) : null;
      // 世系图看哪一朝、圈出谁跟着旧历史的编号,作废
      setPeople({ polity: r && r.kind === 'polity' ? r.id : null, dynasty: null, focus: null });
    }
  };
  // 地图上的地名表换了一份(重推完、看试推演、时间轴跨过地形大事):选中的地方按稳定键换成这一份里的编号;
  // 锚点挪了的(海扩大了……)找同种类同名的那一处(大事前后同一处地方沿用地名),都没有就取消。换了世界的不管
  const shownRef = useRef<Civ | null>(null);
  useLayoutEffect(() => {
    const was = shownRef.current;
    shownRef.current = shownRaw;
    if (!was || !shownRaw || was.places === shownRaw.places || baseRegions(was) !== baseRegions(shownRaw)) return;
    const { sel } = getSelection();
    const p = sel?.kind === 'place' ? was.places[sel.id] : undefined;
    if (!sel || !p) return;
    const r = resolveKey(shownRaw, placeKeyOf(was, sel.id));
    const id = r && r.kind === 'place' ? r.id : shownRaw.places.findIndex((q) => q.kind === p.kind && q.name === p.name);
    if (id < 0) clearSelection();
    else if (id !== sel.id) setSelection({ kind: 'place', id });
  }, [shownRaw]);
  /**
   * 重推好的文明换上去(阶段 4 干预):州、宜居度沿用原来那一份(地理没变;时间轴、地图按它认"还是同一个世界"),
   * 选中的东西、编年史的国家筛选按稳定键换成新历史里的编号(指不到就取消),时间轴从干预那一年接着放(地形大事卡片开着时不动)
   */
  const applyResim = (next: Civ, workerMs: number, eras: EraWorld[] | undefined, baseKey: string) => {
    const old = rawRef.current;
    const sameUps = sameUpheavals(civUps.current, rawUps.current);
    const civ: Civ = old ? reuseRegions(old, next, sameUps, true) : next;
    rawUps.current = civUps.current;
    // 地形大事以后各段的世界:和现在一样(只改了干预)就不换,地图不用重画
    const base = baseRef.current;
    const cur = eraMapsRef.current;
    if (!eras?.length || !base) setEraMaps(null);
    else if (!cur || cur.baseKey !== baseKey || cur.keys.join('|') !== eras.map((e) => e.key).join('|')) setEraMaps(eraMapsOf(base.world, baseKey, eras));
    if (old) remapSelection(old, civ);
    clearChroniclePick();
    setPolityPick(null);
    const info = resimInfo.current;
    if (info) {
      info.workerMs = workerMs;
      info.arrived = performance.now() - info.t0;
      // 平常从生效年份起接着放;地形大事卡片开着时时间轴不动、停下播放(upheavalStore.ts 的 timelineAfterResim)
      if (!info.quiet) timelineAfterResim(Math.min(civ.endYear, Math.max(0, info.year)));
      // 已生效(停 7 秒,带撤销)/ 已撤销(停 4 秒)
      const y = Math.max(0, Math.floor(info.year));
      // 年份照作者的纪年写:"从 1650 年起" / "从公元前 850 年起"
      const era = getEdits().era;
      const at = (n: number) => yearAt(n, era);
      if (info.note) {
        const n = info.note;
        if (n.kind === 'apply') {
          // 这一批新加的命令里有几条没生效(两国不接壤、州里没人住……;原因在概览"我的干预"页)
          const ks = (l: readonly Intervention[]) => l.map((v) => JSON.stringify(v));
          const had = ks(n.before.interventions);
          const done = ks(civ.interventions ?? []);
          const failed = ks(n.after.interventions)
            .filter((k) => !had.includes(k))
            .map((k) => done.indexOf(k))
            .filter((i) => i >= 0 && !interventionOutcome(civ, i).ok).length;
          showToast({
            id: 'resim-done',
            kind: failed ? 'warn' : 'ok',
            text: `已按你说的改写 · 从${spaced(at(y))}重新推演`,
            more: failed ? [`${failed} 条命令没生效,原因见概览的"我的干预"`] : undefined,
            action: n.undo && {
              label: '撤销',
              act: 'rw-undo',
              onClick: () => {
                n.undo?.();
                clearToast('resim-done');
              },
            },
            ttl: 7000,
          });
        } else {
          showToast({ id: 'resim-done', kind: 'ok', text: info.left ? `已撤销改写,从${spaced(at(y))}起重新推演` : `已撤销改写,${at(y)}之后恢复原历史`, ttl: 4000 });
        }
      } else if (info.crown) {
        const undo = info.crown.undo;
        showToast({
          id: 'resim-done',
          kind: 'ok',
          text: `${info.crown.text}；已从${spaced(at(y))}起重新推演`,
          action: undo && {
            label: '撤销',
            act: 'character-restore',
            onClick: () => {
              clearToast('resim-done');
              undo();
            },
          },
          ttl: 7000,
        });
      } else if (info.batch) {
        // 待推演的单子一次推完:几条没生效(两国不接壤、州里没人住……)的原因在概览"我的干预"页
        const { ivs, ups } = info.batch;
        const done = (civ.interventions ?? []).map((x) => JSON.stringify(x));
        const failed = ivs.map((v) => done.indexOf(JSON.stringify(v))).filter((i) => i >= 0 && !interventionOutcome(civ, i).ok).length;
        const n = ivs.length + ups.length;
        showToast({
          id: 'resim-done',
          kind: failed ? 'warn' : 'ok',
          text: `${n - failed} 条命令已生效,已从${spaced(at(y))}起重新推演`,
          more: failed ? [`${failed} 条没生效,原因见概览的"我的干预"`] : undefined,
          action: {
            label: '撤销',
            act: 'iv-batch-undo',
            onClick: () => {
              removeEditsBatch(ivs, ups);
              clearToast('resim-done');
            },
          },
          ttl: 7000,
        });
      } else if (info.added) {
        const v = info.added;
        const named = applyNames(civ, getEdits().names);
        const idx = (civ.interventions ?? []).findIndex((x) => JSON.stringify(x) === JSON.stringify(v));
        // 国家面板下的令:写面板标题上的名字(用户点的那个);那一年它叫别的名字,第二行补一句
        const run = getPanel().run;
        const shown = run && run.from === v.from ? run.shown : undefined;
        const then = interventionActorThen(named, v);
        // 即位:写人物的名字、到哪年下台;没即位成(那年国已亡、他还没出生……)黄色,写原因
        // 方针:"大澜王朝定方针「扩张」",没生效的黄色写原因(同即位)
        // 灭国、让人物去世、改倾向、等下台再即位:"东定国亡，13 州并入大定";将领、名臣去世历史不变,写"历史不变",不写重新推演
        const chars = getEdits().characters;
        const crowned =
          v.kind === 'crown' && !v.after
            ? crownDoneText(applyCharacters(named, chars), v, idx, chars, era)
            : v.kind === 'policy'
              ? policyDoneText(named, v, idx, shown ?? then ?? '', era)
              : newIvDoneText(v.kind === 'crown' ? applyCharacters(named, chars) : named, v, idx, shown ?? then ?? '', era, v.kind === 'crown' ? crownWho(named, v.char, chars) : '');
        showToast({
          id: 'resim-done',
          kind: crowned && !crowned.ok ? 'warn' : 'ok',
          text: crowned
            ? crowned.ok && 'same' in crowned && crowned.same
              ? crowned.text
              : `${crowned.text}；已从${spaced(at(y))}起重新推演`
            : `${eraText(interventionDoneText(named, v, idx, shown), era)},已从${spaced(at(y))}起重新推演`,
          more: !crowned && shown && then && then !== shown ? [`${at(v.from)}时它叫${then}`] : undefined,
          action: {
            label: '撤销',
            onClick: () => {
              const i = getEdits().interventions.findIndex((x) => JSON.stringify(x) === JSON.stringify(v));
              if (i >= 0) removeIntervention(i);
              clearToast('resim-done');
            },
          },
          ttl: 7000,
        });
        // 天灾:提示条开着时,受灾的州在地图上淡淡涂着(地图转过去),提示条收起时一起收起
        const hit = v.kind === 'disaster' && crowned?.ok ? disasterDoneArea(named, v) : [];
        if (hit.length) {
          setCivHighlight({ regions: hit, polities: [], year: v.from, steady: true, faint: true });
          const st = getCivHighlight()?.stamp;
          window.setTimeout(() => getCivHighlight()?.stamp === st && setCivHighlight(null), 7000);
        }
      } else if (info.upAdded) {
        const u = info.upAdded;
        showToast({
          id: 'resim-done',
          kind: 'ok',
          text: `${at(u.year)}${upheavalName(u)} · 从这一年起重新推演`,
          action: {
            label: '撤销',
            onClick: () => {
              const i = (getEdits().upheavals ?? []).findIndex((x) => JSON.stringify(x) === JSON.stringify(u));
              if (i >= 0) removeUpheaval(i);
              clearToast('resim-done');
            },
          },
          ttl: 7000,
        });
      } else if (info.removed || info.upRemoved) {
        showToast({ id: 'resim-done', kind: 'ok', text: info.left ? `已撤销,从${spaced(at(y))}起重新推演` : `已撤销,${at(y)}之后恢复原历史`, ttl: 4000 });
      }
    }
    setRawCiv(civ);
    setResim(null);
    // 打开世界时等着重推完再核对的改名:按推好的历史数对不上的,有就补进打开时那条提示(换了世界、改了地形的不算了)
    const rn = renameCheck.current;
    renameCheck.current = null;
    if (rn && rn.id === currentWorld()?.id && rn.terrain === genTerrain.current) {
      const lost = lostRenames(civ, getEdits().names);
      if (lost) rn.show(lostRenamesNote(lost));
    }
    // 逐年推演的世界推到"现在"了:时间轴只放这一段,播放头停在"现在";刚点了「开始演绎」的接着就往下走
    const play = civPlay.current;
    const rw = rewindNote.current;
    rewindNote.current = null;
    if (play && rw && rw.year === play.year && getStepwise().on && getStepwise().now === play.year) {
      // 刚从这一年重新演绎:界面早就停在这一年了(推的时候点了「接着演绎」的照走),这里只说一声
      const era = getEdits().era;
      showToast({
        id: 'step-rewound',
        kind: 'ok',
        dot: true,
        text: `已回到${yearFull(rw.year, era)}`,
        ttl: 7000,
      });
    } else if (play && cleanPlay(getEdits().play)) {
      enterStepwise(playFromOf(getEdits()), play.year);
      setCivTime({ year: play.year, playing: stepAuto.current, scrubbing: false, story: false });
      stepAuto.current = false;
      // 刚切到别的一支:停在那一支的"现在",说一声,带「切回」原来那支
      const sw = switchNote.current;
      switchNote.current = null;
      if (sw && sw.year === play.year) switchedToast(sw);
    }
    // 刚创建的世界接着往后推完了:缩略图按推完的样子重截,该放历史的从第 0 年放一遍
    if (info?.years && !play) {
      refreshThumb();
      if (storyAfterYears.current) startCivReplay();
      storyAfterYears.current = null;
    }
  };
  const applyResimRef = useRef(applyResim);
  applyResimRef.current = applyResim;

  /**
   * 逐年推演走完一步(worker 的 turn):推得更远的历史换上去(州、宜居度沿用;以前的历史一点没变,选中的东西编号不变),
   * 修改里的进度跟着换(不重推);没收下的干预说一声。是不是该停一下由 Stepwise.tsx 看
   */
  const applyTurn = (next: Civ, play: PlayState, rejected: unknown[], eras: EraWorld[] | undefined, baseKey: string) => {
    // 用的人正按着地图:松开再换上(换历史要重画整张地图,拖着的时候会卡一下)
    if (getStepGesture()) {
      onStepGestureEnd(() => applyTurnRef.current(next, play, rejected, eras, baseKey));
      return;
    }
    const now = cleanPlay(getEdits().play);
    // 换了世界、另开了一次逐年推演、这一步不是接着现在这份进度走的:不要
    if (!now || !getStepwise().on || !getStepwise().busy || play.year <= now.year) return stepLost();
    const old = rawRef.current;
    const sameUps = sameUpheavals(civUps.current, rawUps.current);
    const civ: Civ = old ? reuseRegions(old, next, sameUps, true) : next;
    rawUps.current = civUps.current;
    const base = baseRef.current;
    const cur = eraMapsRef.current;
    if (!eras?.length || !base) setEraMaps(null);
    else if (!cur || cur.baseKey !== baseKey || cur.keys.join('|') !== eras.map((e) => e.key).join('|')) setEraMaps(eraMapsOf(base.world, baseKey, eras));
    civPlay.current = play;
    putPlay(play);
    setRawCiv(civ);
    if (rejected.length) showToast({ id: 'step-rejected', kind: 'warn', text: `${rejected.length} 条干预没能下`, more: ['只能在「现在」干预'], ttl: 5000 });
  };
  const applyTurnRef = useRef(applyTurn);
  applyTurnRef.current = applyTurn;

  /**
   * 再推 N 年推好了(worker 的 extend):前面的历史一点没变,州、宜居度沿用,选中的东西编号不变;
   * 推演年数存进修改(存档、自动存、分享链接都记着推到哪),播放头停在原处。
   * 顶上提示条「从第 N 年接着看」(从原来的结束年份按现在的速度往后放,导播开着就导播放)、「撤销」(换回推之前那一份)
   */
  const applyExtended = (xid: number, next: Civ, to: number, ms: number, eras: EraWorld[] | undefined, baseKey: string) => {
    const x = extendRef.current;
    const old = rawRef.current;
    if (!x || x.xid !== xid || !old) return;
    // 用的人正按着地图(拖、捏合、滚轮):松开再换上(换历史要重画整张地图、重排时间轴,拖着的时候会卡一下)
    if (getStepGesture()) {
      onStepGestureEnd(() => applyExtendedRef.current(xid, next, to, ms, eras, baseKey));
      return;
    }
    extendRef.current = null;
    setExtendBusy(null);
    const sameUps = sameUpheavals(civUps.current, rawUps.current);
    const civ: Civ = reuseRegions(old, next, sameUps, true);
    rawUps.current = civUps.current;
    const base = baseRef.current;
    const cur = eraMapsRef.current;
    if (!eras?.length || !base) setEraMaps(null);
    else if (!cur || cur.baseKey !== baseKey || cur.keys.join('|') !== eras.map((e) => e.key).join('|')) setEraMaps(eraMapsOf(base.world, baseKey, eras));
    // 有地形大事的世界是从第 0 年整段推的
    noteExtendSpeed(civUps.current?.length ? 0 : x.from, to, ms);
    // 先记下推到哪年,修改里的推演年数跟着换时不再重推一遍
    civYears.current = cleanEndYear(to);
    // 播放头停在原处:推的时候放到了原来的结束年份(停在"现在")的,钉在那一年(不然换上以后"现在"成了新的结尾)
    if (getCivTime().year === null) setCivTime({ year: x.from });
    setRawCiv(civ);
    setEndYear(to);
    setExtendFresh({ from: x.from, to });
    refreshThumb();
    dropExtendUndo();
    extendUndo.current = { before: old, after: civ, from: x.from, endYear: x.endYear, timer: window.setTimeout(dropExtendUndo, EXTEND_UNDO_MS) };
    // 提示条等新的历史画上去以后再出(新添几件大事要数整段编年史,时间轴那时已经算好了,不再算一遍)
    extendDone.current = { xid, from: x.from, to, ms, t0: x.t0, arrived: performance.now() - x.t0 };
  };
  const applyExtendedRef = useRef(applyExtended);
  applyExtendedRef.current = applyExtended;
  /** 刚推好、提示条还没出的那一次 */
  const extendDone = useRef<{ xid: number; from: number; to: number; ms: number; t0: number; arrived: number } | null>(null);
  useEffect(() => {
    const d = extendDone.current;
    if (!d || !realCiv || realCiv.endYear !== d.to) return;
    extendDone.current = null;
    // 新添几件大事(和时间轴上默认画的"大事"同一个口径)
    const fresh = filterChronicle(fullChronicle(realCiv), { major: true, polity: null }).filter((e) => e.year > d.from).length;
    const era = getEdits().era;
    showToast({
      id: 'extend-done',
      kind: 'ok',
      dot: true,
      text: `已推到${yearFull(d.to, era)}`,
      more: [`新添 ${fresh} 件大事`],
      actions: [
        {
          label: narrowRef.current ? '接着看' : `从${yearFull(d.from, era)}接着看`,
          primary: true,
          act: 'extend-watch',
          onClick: () => {
            clearToast('extend-done');
            setCivTime({ year: d.from, playing: true, scrubbing: false, story: false });
          },
        },
        { label: '撤销', act: 'extend-undo', onClick: () => undoExtendRef.current() },
      ],
      ttl: EXTEND_TOAST_MS,
    });
    (window as unknown as { __wfExtend: unknown }).__wfExtend = { xid: d.xid, from: d.from, to: d.to, workerMs: d.ms, arrivedMs: d.arrived, shownMs: performance.now() - d.t0, fresh };
  }, [realCiv]);
  /** 提示条收起以后不能撤销了:推之前那一份放掉 */
  const dropExtendUndo = () => {
    const u = extendUndo.current;
    if (u) clearTimeout(u.timer);
    extendUndo.current = null;
  };
  /** 提示条上的「撤销」:回到推之前 —— 历史换回推之前那一份(一模一样),推演年数改回去 */
  const undoExtend = () => {
    clearToast('extend-done');
    const u = extendUndo.current;
    dropExtendUndo();
    if (!u || extendRef.current) return;
    setExtendFresh(null);
    const t = getCivTime();
    if (t.year !== null && t.year > u.from) setCivTime({ year: u.from, playing: false, scrubbing: false, story: false });
    if (rawRef.current === u.after) {
      civYears.current = cleanEndYear(u.from);
      remapSelection(u.after, u.before);
      setRawCiv(u.before);
      refreshThumb();
    }
    // 推完以后又改过别的(干预……):只把推演年数改回去,照常重推。修改里原来没写推演年数的(3000 年)照样不写
    setEndYear(u.endYear);
  };
  const undoExtendRef = useRef(undoExtend);
  undoExtendRef.current = undoExtend;
  // 「再推」:接到后台线程上(ExtendYears.tsx 调 extendStart / extendStop)
  useEffect(() => {
    setExtendRunner({
      start: (years) => {
        const p = genParams.current;
        const raw = rawRef.current;
        if (!p || !raw || fresh.current || extendRef.current || previewOn.current || getStepwise().on || cleanPlay(getEdits().play)) return;
        const from = raw.endYear;
        const to = extendedEndYear(from, years);
        if (!(to > from)) return;
        // 照原样打开的旧世界:推演要用新版的规则,先问要不要另存一份(在那一份上推)
        if (askHistory({ ...getEdits(), endYear: to })) return;
        const xid = ++extendSeq.current;
        extendRef.current = { xid, from, to, t0: performance.now(), endYear: getEdits().endYear };
        clearToast('extend-done');
        dropExtendUndo();
        // 停在"现在"(结束年份)的播放头钉在这一年:时间轴变长以后还停在原处
        if (getCivTime().year === null) setCivTime({ year: from });
        setExtendFresh(null);
        setExtendBusy({ xid, from, to, year: null, pct: 0, slow: !!civUps.current?.length });
        send({
          type: 'extend',
          id: reqId.current,
          xid,
          to,
          params: p,
          terrain: [...genTerrain.current],
          sketch: genSketch.current,
          interventions: [...civEdits.current],
          ...upsOpt(civUps.current),
          ...namesOpt(civNames.current),
          ...setupOpt(civSetup.current),
          have: [...eraPatches.current.keys()],
        });
      },
      stop: () => {
        const x = extendRef.current;
        if (!x) return;
        const b = getExtend().busy;
        extendRef.current = null;
        setExtendBusy(null);
        // 从第 0 年整段推的(有地形大事、线程被重开过:一直没有分段进度)中途停不下来:线程手上只剩这一件活时换一个新的线程
        // (手上的世界下次用到时按参数重算),不然要等它整段推完才空出来
        if (b?.xid === x.xid && b.year === null && busyRef.current === 1) {
          idleWorker(true);
          return;
        }
        // 叫停不算一件活(线程不回音):直接发
        workerRef.current?.postMessage({ type: 'extendStop', id: reqId.current, xid: x.xid } satisfies WorkerRequest);
      },
    });
    return () => setExtendRunner(null);
  }, [send]);

  /** 照大纲推演查完一条 / 开始查一条 / 开始硬改:侧栏、大纲页的进度,顶上的提示条 */
  const outlineProgress = (oid: number, done: number, total: number, review: PlotReview[], at?: { id: number; fix: number | null; trial?: { n: number; of: number } }) => {
    const o = outlineRef.current;
    if (!o || o.oid !== oid) return;
    const run = { oid, done, total, review, at: at?.id ?? null, fix: at?.fix ?? null, trial: at?.trial ?? null };
    setOutlineRun(run);
    const c = realCivRef.current;
    if (c) showToast(outlineRunToast(run, { civ: c, plots: o.plots, review, marks: getEdits().marks, characters: getEdits().characters }, getEdits().era, stopOutlineRun, isNarrow()));
  };
  const outlineProgressRef = useRef(outlineProgress);
  outlineProgressRef.current = outlineProgress;
  /**
   * 照大纲推演好了:干预串(作者的 + 硬改出来的)、批改记进修改(一步,⌘Z 回到推之前),整段历史直接换上(不再重推一遍);
   * 推的时候大纲、作者自己的干预、标记、人物变了:不换上(批改是照推之前那一份算的;大纲、干预变了那边会照新的重推)
   */
  const applyOutlined = (oid: number, next: Civ, ivs: Intervention[], review: PlotReview[], ms: number, eras: EraWorld[] | undefined, baseKey: string) => {
    const o = outlineRef.current;
    if (!o || o.oid !== oid) return;
    if (getStepGesture()) {
      onStepGestureEnd(() => applyOutlinedRef.current(oid, next, ivs, review, ms, eras, baseKey));
      return;
    }
    endOutline();
    const e = getEdits();
    if (JSON.stringify(e.outline?.plots ?? null) !== JSON.stringify(o.plots) || !sameInterventions(ownInterventions(e.interventions), o.own)) return;
    if (JSON.stringify(e.marks ?? null) !== o.marks || JSON.stringify(e.characters ?? null) !== o.characters) {
      showToast({ id: 'outline-done', kind: 'warn', text: '推的时候改了标记或人物，结果没换上', more: ['再点一次「照大纲推演」'], ttl: 7000 });
      return;
    }
    // 先记下这串干预推好了,修改换上时不再重推
    const before = civEdits.current;
    civEdits.current = ivs;
    if (!putOutlineResult(o.plots, review, ivs)) {
      civEdits.current = before;
      return;
    }
    resimInfo.current = null;
    applyResim(next, ms, eras, baseKey);
    showToast(outlineDoneToast(review, () => openOverview('outline')));
  };
  const applyOutlinedRef = useRef(applyOutlined);
  applyOutlinedRef.current = applyOutlined;
  /** 叫停照大纲推演:世界还是推之前那样 */
  const stopOutlineRun = () => {
    const o = outlineRef.current;
    if (!o) return;
    endOutline();
    // 叫停不算一件活(线程不回音):直接发
    workerRef.current?.postMessage({ type: 'outlineStop', id: reqId.current, oid: o.oid } satisfies WorkerRequest);
  };
  // 「照大纲推演」:接到后台线程上(大纲页、侧栏先问多认真地试(OutlineRunAsk),再调 startOutline / stopOutline)
  useEffect(() => {
    setOutlineRunner({
      start: (tries) => {
        const p = genParams.current;
        const raw = rawRef.current;
        const e = getEdits();
        const plots = e.outline?.plots;
        if (!p || !raw || !plots?.length || outlineRef.current || previewOn.current || getStepwise().on || cleanPlay(e.play)) return;
        // 世界还在生成、在重推、在再推:等它推完
        if (fresh.current || regenRef.current || civLater.current || resimInfo.current || extendRef.current) {
          showToast({ id: 'outline', kind: 'info', text: '世界还在推演，推完再照大纲推演', ttl: 4000 });
          return;
        }
        // 照原样打开的旧世界:推演要用新版的规则,先问要不要另存一份(在那一份上推)
        if (askHistory(e)) return;
        const oid = ++outlineSeq.current;
        const own = ownInterventions(e.interventions);
        outlineRef.current = { oid, plots, own, marks: JSON.stringify(e.marks ?? null), characters: JSON.stringify(e.characters ?? null), t0: performance.now() };
        clearToast('outline-done');
        outlineProgress(oid, 0, plots.length, [], undefined);
        send({
          type: 'outline',
          id: reqId.current,
          oid,
          plots,
          tries,
          params: p,
          terrain: [...genTerrain.current],
          sketch: genSketch.current,
          interventions: [...e.interventions],
          ...(e.characters?.length ? { characters: e.characters } : {}),
          ...(e.marks?.length ? { marks: e.marks } : {}),
          ...upsOpt(civUps.current),
          ...namesOpt(civNames.current),
          ...yearsOpt(civYears.current),
          ...setupOpt(civSetup.current),
          have: [...eraPatches.current.keys()],
        });
      },
      stop: stopOutlineRun,
    });
    return () => setOutlineRunner(null);
  }, [send]);

  // ---- 生成 ----
  /** 按 t 的参数、地形修改生成世界;生成完(readyRef)套上 t 的修改 */
  const generate = useCallback(
    (t: Target) => {
      // 原来那个世界等着截的缩略图(编辑地形停笔没多久)先截下来,换走以后就截不到了
      flushThumb();
      targetRef.current = t;
      const p = t.params;
      const id = ++reqId.current;
      genParams.current = p;
      setParams(p);
      setProgress({ stage: '准备', pct: 0, seed: p.seed });
      // 手机:新世界、打开存档都要看地图 —— 拉到顶的世界卡片先收起来
      setWorldSheet('peek');
      // 改过地形、画过草图的世界直接带着它们生成,不用先生成原样再重新生成一遍
      const terrain = t.edits.terrain;
      genTerrain.current = terrain;
      genSketch.current = t.edits.sketch;
      fresh.current = true;
      regenRef.current = null;
      // 换了世界:编辑地形时不起名的那一段、要补推的历史都不算了(新世界带着历史生成)
      endNamesHold();
      setTerrainStatus({ busy: false });
      setShownTerrain(terrain);
      setShownSketch(t.edits.sketch);
      setTerrainTool({ on: false });
      closeUpheaval();
      closeSaveAsNew();
      // 地名风格也直接带着(只管起名,和改名、干预不同:生成完不用再重推一遍)
      civNames.current = t.edits.nameMix;
      // 推演年数同样直接带着(新建中的世界先推 3000 年)
      civYears.current = yearsFor(t.kind === 'draft' && !t.fullCiv, t.edits);
      civSetup.current = setupFor(t.kind === 'draft' && !t.fullCiv, t.edits);
      storyAfterYears.current = null;
      // 新建的世界能编辑地形:线程留着整张主图,第一笔就能只重铺变了的那块。
      // 新建界面先看的是地图(星球),推几千年的历史比生成地形、铺像素慢:地图先交、先换上,历史随后(mapFirst);
      // 写实画风的整张像素层也让线程画好随地图交来(paint),换上之前主线程不用自己再分小步画
      const req: WorkerRequest = { type: 'generate', id, params: p, scale: 1, terrain: [...terrain], sketch: t.edits.sketch, ...namesOpt(t.edits.nameMix), ...yearsOpt(civYears.current), ...setupOpt(civSetup.current), ...(t.kind === 'draft' ? { keep: true, mapFirst: true as const, paint: paintLooks(drawKey.current, mapViewRef.current.sat) } : {}), renames: t.edits.names };
      mapFirst.current = null;
      setMapEarly(false);
      frozenLoad.current = null;
      genReq.current = null;
      const save = oldStored(t);
      // 存着的、旧版本建的世界:浏览器里有它那一版的原件就照原样打开(读原件,不重新生成);没有才按现在的规则生成
      if (save) {
        genReq.current = req;
        void frozenResult(t.id, save).then((r) => {
          if (id !== reqId.current) return;
          if (!r || r === 'broken') {
            if (r) frozenBroken.current = t.id;
            genReq.current = null;
            return send(req);
          }
          // 原件里的历史就是带着存档里的干预、地形大事(逐年推演的:推到"现在")推出来的:套上以后不用重推
          frozenLoad.current = { id: t.id, gen: save.generator };
          loadedFrozen.current = true;
          civEdits.current = t.edits.interventions;
          civUps.current = genUps.current = t.edits.upheavals;
          const play = cleanPlay(t.edits.play);
          civPlay.current = play;
          // 带上进度:线程按它记下这份历史,下一步从这里接着推(不从第 0 年重推)
          send({ type: 'load', id, params: p, scale: 1, parts: r.parts, terrain: [...terrain], sketch: t.edits.sketch, ...upsOpt(t.edits.upheavals), interventions: [...t.edits.interventions], ...namesOpt(t.edits.nameMix), ...yearsOpt(civYears.current), ...setupOpt(civSetup.current), ...(play ? { play } : {}), renames: t.edits.names });
        });
      } else send(req);
      loadedFrozen.current = false;
      // 换世界:改名、干预、选中都属于旧世界,一起作废(先停掉旧世界的自动存,清空不算"改回默认";新世界先按"没有干预、没有地形大事"生成)
      detachWorld();
      leaveStepwise();
      switchNote.current = null;
      resimText.current = null;
      civEdits.current = EMPTY_EDITS.interventions;
      civUps.current = genUps.current = undefined;
      civPlay.current = undefined;
      resimSeq.current++;
      resimInfo.current = null;
      setResim(null);
      // 再推:正在推的不要了,弹层收起,刚推的那段不标,旧世界的「撤销」作废
      extendRef.current = null;
      extendDone.current = null;
      resetExtend();
      dropExtendUndo();
      clearToast('extend-done');
      setPolityPick(null);
      clearEdits();
      clearSelection();
      if (getPeople().polity !== null) setPeople({ polity: null });
      // 正在进行 / 已算好的回放都属于旧世界,一起作废
      setReplay(null);
      setReplayOn(false);
      // 种子、参数写进网址(分享链接时对方看到的是同一个世界);存着的世界带上编号
      writeWorldUrl(t);
    },
    [send],
  );

  useEffect(() => {
    // 邀请链接(invite=):记下邀请码,从网址里去掉(在记第一步之前去掉,按后退时不会再带回来)
    const invited = takeInviteFromUrl();
    // 浏览器的后退、前进:这一页记成第一步,之后每换一个画面记一步(nav.ts)
    const stopNav = startNav(wall ? { page: 'gallery', ...(wall.kind === 'work' ? { id: wall.id } : {}) } : navInfo(route.stage, route.target), {
      route: (to, from, dir) => navRef.current.route(to, from, dir),
      describe: () => navRef.current.describe(),
      settled: () => navRef.current.settled(),
      apply: (l) => navRef.current.apply(l),
      url: keepView,
    });
    // 分享链接:先把 # 那段从地址栏去掉(刷新不会重复导入),解开以后走读档流程;
    // 链接里的种子、参数和网址上的一样,所以照常先按网址生成,不用等
    if (init.share) {
      // own=1:最新版和旧网站之间交过来的自己的世界(看原样、到最新版打开),不说成别人分享的;标记用过就从地址栏去掉
      const q = new URLSearchParams(location.search);
      const own = q.get(OWN_KEY) === '1';
      q.delete(OWN_KEY);
      const rest = `${q}`;
      navUrl(location.pathname + (rest ? `?${rest}` : ''));
      const at = getNav();
      // 解开之前按了后退 / 前进(到了别的画面):不打开
      decodeShare(init.share).then((r) => {
        if (sameScreen(getNav(), at)) openShareRef.current(r, undefined, own);
      });
    }
    // 朋友的预设链接:先把 # 那段从地址栏去掉(刷新不会再来一遍)。短链接后面的"打开时看哪"等取到存档再去掉(没取到、刷新重来时还在)
    if (init.preset) navUrl(location.pathname + location.search);
    if (presetLink) presetOpened(presetLink);
    // 邀请链接:弹出登录窗(已经登录了就算了)
    if (invited && serverBase() && !getSession()) openLogin();
    if (route.target) generate(route.target);
    else if (landing === 'loading') openShortShare(init.shortShare ?? '');
    // 作品墙:网址换成 ?gallery(=编号)的写法(# 后面写的也换过来);带编号的去取那个作品
    else if (wall) {
      if (wall.kind === 'work') openWork(wall.id);
      else writeGalleryUrl('');
    }
    // 刷新回来的照图新建(new=image)留着,弹窗点了「开始」或「取消」才换掉,再刷新还能回到弹窗
    else if (!route.dialog) writeHomeUrl();
    if (route.gone !== undefined) goneToast(route.gone);
    // 页面开着时又粘贴了一个只有 # 不同的分享链接(浏览器不刷新页面)
    const onHash = () => {
      const h = location.hash;
      // 页面开着时又粘贴了朋友的预设链接:回到我的世界,打开填好参数的新建弹窗
      if (isPresetHash(h)) {
        navAdopt(navInfo(getStage().stage, targetRef.current));
        navUrl(location.pathname + location.search);
        const r = decodePresetHash(h);
        if (r.ok) {
          if (getStage().stage !== 'home') showHomeRef.current();
          // 新开一个弹窗(开着的那个里填的东西不留)
          setNewDlg({ ...presetDialog(r.preset), stamp: performance.now() });
        }
        presetOpened(r);
        return;
      }
      // 页面开着时又贴了作品墙的地址(#gallery、#gallery=<编号>):到作品墙那一页 / 打开那个作品。
      // 浏览器为这个 # 记的那一步直接记成作品墙的,下面换过去时只改这一步(不再多记一步,按一次后退就回到原来的画面)
      const gid = galleryOfUrl(new URLSearchParams(), h);
      if (gid !== null) {
        navAdopt({ page: 'gallery', ...(gid ? { id: gid } : {}) });
        navUrl(location.pathname + location.search);
        if (gid) wallRef.current.open(gid);
        else wallRef.current.list();
        return;
      }
      if (!isShareHash(h)) {
        // 地址栏里自己加了别的 #:浏览器记了一步、这个网站没记过,也记成一步(不然收起卡片退回去时会落到它上面)
        if (!isNavState(history.state)) navAdopt(navInfo(getStage().stage, targetRef.current));
        return;
      }
      // 浏览器为这个 # 记了一步:当成新的一步(打开分享的世界时换成它)
      navAdopt(navInfo(getStage().stage, targetRef.current));
      navUrl(location.pathname + location.search);
      const at = getNav();
      decodeShare(h).then((r) => {
        if (sameScreen(getNav(), at)) openShareRef.current(r);
      });
    };
    window.addEventListener('hashchange', onHash);
    return () => {
      stopNav();
      window.removeEventListener('hashchange', onHash);
      workerRef.current?.terminate();
      workerRef.current = null;
    };
    // 只在首次挂载时自动生成;之后由操作触发
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- 改地形(阶段 4):地形修改、草图一变,就在后台带着新地形重新生成世界(连同当时的干预重推文明;
  // 州、历史整个重来,改名和干预按稳定键尽量套上)。写在干预的前面:同时变了的话,干预跟着这次生成一起推 ----
  useEffect(() => {
    const t = edits.terrain;
    const sk = edits.sketch;
    if (!baseData || !genParams.current || fresh.current || (sameTerrain(t, genTerrain.current) && sameSketch(sk, genSketch.current))) return;
    const id = ++reqId.current;
    const interventions = getEdits().interventions;
    const ups = getEdits().upheavals;
    // 编辑地形时不起名(namesHold):新建世界里开着编辑地形涂了一笔,就进这一段,地图上的地名先收起来;
    // 这一段里只换地形、不推历史(照手绘图新建换了张图长出星球不算一笔)
    const img = (s?: SketchEdit) => (s?.image ? `${s.image.name}
${s.image.cells}` : null);
    if (!namesHold.current && getTerrainTool().on && getStage().stage === 'draft' && img(sk) === img(genSketch.current)) {
      namesHold.current = { tip: false };
      setNamesHeld(true);
    }
    const skipCiv = !!namesHold.current;
    // 正在补推的历史是上一个地形的:作废(线程那边被新的生成顶掉)
    if (naming.current) {
      naming.current = null;
      setNamingPct(null);
    }
    genTerrain.current = t;
    genSketch.current = sk;
    civEdits.current = interventions;
    civUps.current = genUps.current = ups;
    civNames.current = getEdits().nameMix;
    civYears.current = yearsFor(plainDraft(), getEdits());
    civSetup.current = setupFor(plainDraft(), getEdits());
    resimSeq.current++;
    resimInfo.current = null;
    setResim(null);
    regenRef.current = { id, t0: performance.now(), terrain: t, sketch: sk };
    regenNote.current = takeRewriteNote(getEdits());
    setTerrainStatus((s) => ({ ...s, busy: true }));
    setProgress({ stage: '准备', pct: 0, regen: true });
    // 回放、选中、编年史和人物页的国家筛选都属于旧地形上的历史
    setReplay(null);
    setReplayOn(false);
    clearSelection();
    setPolityPick(null);
    clearChroniclePick();
    if (getChronicle().polity !== null) setChronicle({ polity: null });
    if (getPeople().polity !== null) setPeople({ polity: null });
    // 线程还留着地图上那张整图(baseKeyRef):只重铺、只交回变了的那块
    send({ type: 'generate', id, params: genParams.current, scale: 1, terrain: [...t], sketch: sk, interventions: [...interventions], ...upsOpt(ups), ...namesOpt(civNames.current), ...yearsOpt(civYears.current), ...setupOpt(civSetup.current), keep: getStage().stage === 'draft', ...(baseKeyRef.current ? { from: baseKeyRef.current } : {}), ...(skipCiv ? { skipCiv: true as const } : {}) });
  }, [edits.terrain, edits.sketch, baseData, send]);

  /** 补推地图上这个世界的历史、起地名(编辑地形时生成的没推历史):带着和生成时一样的干预、地形大事、地名风格、推演年数、拓荒、起源 */
  const startNames = () => {
    const p = genParams.current;
    if (!civLater.current || naming.current || fresh.current || !p) return;
    const nid = ++namingSeq.current;
    naming.current = { nid, t0: performance.now() };
    setNamingPct(0);
    send({ type: 'civOnly', id: reqId.current, nid, params: p, terrain: [...genTerrain.current], sketch: genSketch.current, interventions: [...civEdits.current], ...upsOpt(civUps.current), ...namesOpt(civNames.current), ...yearsOpt(civYears.current), ...setupOpt(civSetup.current) });
  };
  const startNamesRef = useRef(startNames);
  startNamesRef.current = startNames;
  /** 收起编辑地形(点「完成」……):不起名的这一段结束,地图上的世界没推历史就补推、起地名 */
  const releaseNames = () => {
    if (!namesHold.current) return;
    namesHold.current = null;
    // 还在按新地形重新生成:换上以后接着补推(terrainDoneRef);这期间地图上还是涂之前的历史,照旧不标地名
    const rg = regenRef.current;
    if (rg && rg.arrived === undefined) return;
    setNamesHeld(false);
    startNames();
  };
  const releaseNamesRef = useRef(releaseNames);
  releaseNamesRef.current = releaseNames;
  useEffect(() => {
    // 存档缩略图:编辑地形开着时连着涂不截,收起时等着的那一张不再等
    setThumbEditing(terrainTool.on);
    if (!terrainTool.on) releaseNamesRef.current();
  }, [terrainTool.on]);
  /** 补推好了:换上(地名淡入);对不上的改名、没生效的干预(以别的世界为底稿新建时带着的)照旧说一句 */
  const namesDone = (nid: number, civ: Civ, civMs: number) => {
    if (naming.current?.nid !== nid) return;
    naming.current = null;
    civLater.current = false;
    civMsLast.current = civMs;
    noteExtendSpeed(0, civ.endYear, civMs);
    const b = baseRef.current;
    lastReady.current = b ? { world: b.world, civ } : null;
    setRawCiv(civ);
    setNamingPct(null);
    setNamesIn(nid);
    const e = getEdits();
    const lostNames = Object.keys(e.names).filter((k) => !resolveKey(civ, k)).length;
    const lostInterventions = (civ.interventions ?? []).filter((_, i) => !interventionOutcome(civ, i).ok).length;
    const lost = [lostNames ? `${lostNames} 处改名` : '', lostInterventions ? `${lostInterventions} 条干预` : ''].filter(Boolean);
    if (lost.length) showToast({ id: 'terrain', kind: 'warn', text: '已按新地形重新生成', more: [`${lost.join('、')}暂未生效`] });
  };
  const namesDoneRef = useRef(namesDone);
  namesDoneRef.current = namesDone;

  /**
   * 地图上这份历史推的时候带的(干预、地形大事、地名风格、推演年数、拓荒起源、逐年推演的进度)和这份修改不一样 = 下面那段要在后台重推。
   * 和下面那段开头的判断一样(新建中的世界不看年数、拓荒起源、进度);读档时用:要重推的,改名等推完再核对
   */
  const historyBehind = (e: WorldEdits, isDraft: boolean) =>
    !sameInterventions(e.interventions, civEdits.current) ||
    !sameUpheavals(e.upheavals, civUps.current) ||
    !sameMix(e.nameMix, civNames.current) ||
    (!(isDraft && !targetRef.current?.fullCiv) && cleanEndYear(e.endYear) !== civYears.current) ||
    !sameSetup(setupFor(isDraft && !targetRef.current?.fullCiv, e), civSetup.current) ||
    JSON.stringify((isDraft ? undefined : cleanPlay(e.play)) ?? null) !== JSON.stringify(civPlay.current ?? null);
  // ---- 干预(阶段 4)、地形大事:干预列表或地形大事一变,就在后台带着新的重推文明(地形不动;变了的那一年以前和原来一样) ----
  useEffect(() => {
    const list = edits.interventions;
    const ups = edits.upheavals;
    const names = edits.nameMix;
    // 地名风格:生成新世界时已经带着(修改先清空、生成完再套上,这期间不算变了);新建时换了风格,只重推、重新起名
    const sameNames = fresh.current || sameMix(names, civNames.current);
    // 推演年数:新建中的世界一律先推 3000 年(不因为调了年数重推);创建以后按世界自己的年数,和推好的不一样就接着推
    // (照故事找世界选中的结果:新建中也按自己的推演年数、拓荒、起源、天灾推,和搜的时候一样)
    const plain = plainDraft();
    const endYear = plain ? civYears.current : cleanEndYear(edits.endYear);
    const sameYears = fresh.current || endYear === civYears.current;
    // 拓荒、起源:同推演年数,新建中的世界一律按默认推;创建以后按世界自己的,整段历史从第 0 年重推(文明种子新建中就照它推)
    const setup = setupFor(plain, edits);
    const sameSet = fresh.current || sameSetup(setup, civSetup.current);
    // 逐年推演的进度:打开逐年推演的世界、开始逐年推演时按它推到"现在";一步步走的时候进度和推好的那份一样,不重推
    const play = draft ? undefined : cleanPlay(edits.play);
    const samePlay = fresh.current || JSON.stringify(play ?? null) === JSON.stringify(civPlay.current ?? null);
    if (!baseData || !genParams.current || (sameInterventions(list, civEdits.current) && sameUpheavals(ups, civUps.current) && sameNames && sameYears && sameSet && samePlay)) return;
    if (!sameTerrain(getEdits().terrain, genTerrain.current) || !sameSketch(getEdits().sketch, genSketch.current)) return; // 等改地形那次生成一起推
    // 从哪一年起变:新加的 / 删掉的干预、地形大事里最早的那一年(重推完时间轴停在这里)
    const before = civEdits.current;
    const d = multisetDiff(list, before);
    const changed = [...d.added, ...d.removed];
    const upBefore = civUps.current ?? [];
    const upNow = ups ?? [];
    const ud = multisetDiff(upNow, upBefore);
    const upChanged = [...ud.added, ...ud.removed];
    const years = [...(changed.length || upChanged.length ? changed : list).map((v) => Math.floor(v.from)), ...upChanged.map((u) => u.year)].filter((y) => Number.isFinite(y));
    // 只换了推演年数:从原来和现在的结束年份里早的那一年起变(之前的历史不变)
    const oldEnd = civYears.current ?? END_YEAR_DEFAULT;
    const newEnd = endYear ?? END_YEAR_DEFAULT;
    const yearsOnly = !sameYears && sameSet && !changed.length && !upChanged.length && sameInterventions(list, before) && sameUpheavals(ups, civUps.current);
    // 只换了拓荒、起源(创建世界那一刻):从第 0 年起都变了
    const setupOnly = !sameSet && !changed.length && !upChanged.length && sameInterventions(list, before) && sameUpheavals(ups, civUps.current);
    const year = !sameSet ? 0 : yearsOnly ? Math.min(oldEnd, newEnd) : years.length ? Math.max(0, Math.min(...years)) : 0;
    // 只换了地名风格(或推演年数):历史不变,不提示、不跳时间
    const namesOnly = !changed.length && !upChanged.length && sameInterventions(list, before) && sameUpheavals(ups, civUps.current);
    civEdits.current = list;
    civUps.current = ups;
    if (!fresh.current) civNames.current = names;
    if (!fresh.current) civYears.current = endYear;
    if (!fresh.current) civSetup.current = setup;
    if (!fresh.current) civPlay.current = play;
    // 地图上这个世界还没推历史(编辑地形时生成的):不重推,补推时带着新的一起推(正在补推的这就按新的重来)
    if (civLater.current) {
      const rg = regenRef.current;
      if (namesHold.current || (rg && rg.arrived === undefined)) return;
      naming.current = null;
      startNamesRef.current();
      return;
    }
    const seq = ++resimSeq.current;
    // 只多了一条 = 新下的干预 / 新加的大事;只少了一条 = 撤销(读档、自动恢复套上的不算,不提示)
    const quiet = namesOnly || (list === restoredIv.current && ups === restoredUps.current);
    const one = changed.length + upChanged.length === 1;
    const added = !quiet && one && list.length === before.length + 1 ? changed[0] : undefined;
    const removed = !quiet && one && list.length === before.length - 1 ? changed[0] : undefined;
    const upAdded = !quiet && one && upNow.length === upBefore.length + 1 ? upChanged[0] : undefined;
    const upRemoved = !quiet && one && upNow.length === upBefore.length - 1 ? upChanged[0] : undefined;
    const note = takeRewriteNote(getEdits()) ?? undefined;
    const crown = takeCrownResim(getEdits()) ?? undefined;
    // 待推演的单子一次加了几条(pendingStore 记着真加上了的那几条)
    const pushed = takePendingBatch(getEdits());
    const batch = !quiet && !note && pushed && pushed.ivs.length + pushed.ups.length > 1 ? pushed : undefined;
    // 逐年推演:推到"现在"就停(提示条上写推到哪一年);别的照旧
    const stepOnly = !!play && !samePlay && sameInterventions(list, before) && sameUpheavals(ups, civUps.current);
    resimInfo.current = {
      seq,
      year: stepOnly ? 0 : year,
      t0: performance.now(),
      ...(crown ? { crown } : { added, removed, upAdded, upRemoved, batch }),
      left: list.length + upNow.length,
      quiet: quiet || stepOnly,
      note,
      years: yearsOnly || setupOnly,
    };
    // 切支线:提示条写切到哪一支(只用这一次)
    const text = stepOnly && resimText.current ? resimText.current : undefined;
    resimText.current = null;
    setResim({ year: stepOnly ? 0 : year, end: play ? play.year : newEnd, ...(text ? { text } : {}) });
    send({
      type: 'resim',
      id: reqId.current,
      seq,
      params: genParams.current,
      terrain: [...genTerrain.current],
      sketch: genSketch.current,
      interventions: list,
      ...upsOpt(ups),
      ...namesOpt(civNames.current),
      ...yearsOpt(civYears.current),
      ...setupOpt(civSetup.current),
      ...(play ? { play } : {}),
      have: [...eraPatches.current.keys()],
    });
  }, [edits.interventions, edits.upheavals, edits.nameMix, edits.endYear, edits.frontier, edits.origins, edits.civSeed, edits.calamity, edits.play, draft, baseData, send]);
  // 地图上这份历史的摘要(检查脚本对比逐年推演、存回推演模式以后是不是同一段历史用):before 年以前的史事条数和指纹、立过几国
  useEffect(() => {
    const c = rawCiv;
    (window as unknown as { __wfCivSum: unknown }).__wfCivSum = (before: number) => {
      if (!c) return null;
      const a = c.annals.filter((x) => x.year < before);
      const s = JSON.stringify(a);
      let h = 0;
      for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
      return { endYear: c.endYear, annals: a.length, hash: h, polities: c.polities.filter((p) => p.founded < before).length };
    };
  }, [rawCiv]);
  // 重推的文明画到地图上以后,记下"从下命令到地图更新"用了多久(冒烟检查用)
  useEffect(() => {
    const info = resimInfo.current;
    if (!info || info.arrived === undefined || !rawCiv) return;
    const drawn = performance.now() - info.t0;
    requestAnimationFrame(() => {
      (window as unknown as { __wfResim: unknown }).__wfResim = {
        seq: info.seq,
        year: info.year,
        workerMs: info.workerMs,
        arrivedMs: info.arrived,
        drawnMs: drawn,
        paintedMs: performance.now() - info.t0,
      };
    });
    resimInfo.current = null;
  }, [rawCiv]);

  /**
   * 按新地形重新生成完(阶段 4 改地形):记下新的地形校验(自动存的存档跟着改);
   * 数一数改名、干预有几处在新历史里对不上(面板里提示"暂未生效")
   */
  const terrainDoneRef = useRef<(world: World, civ: Civ | null, ms: number) => void>(() => {});
  terrainDoneRef.current = (world: World, rc: Civ | null, ms: number) => {
    const rg = regenRef.current;
    if (!rg) return;
    rg.workerMs = ms;
    rg.arrived = performance.now() - rg.t0;
    // 没推历史的(编辑地形时不起名):补推完再记
    lastReady.current = rc ? { world, civ: rc } : null;
    setShownTerrain(rg.terrain);
    setShownSketch(rg.sketch);
    const e = getEdits();
    if (sameTerrain(e.terrain, rg.terrain) && sameSketch(e.sketch, rg.sketch)) updateCheck(worldCheck(world));
    const lostNames = rc ? Object.keys(e.names).filter((k) => !resolveKey(rc, k)).length : 0;
    // 干预:和世界概览"我的干预"页一个口径(这份历史带着哪些干预推的、哪几条没生效,见 chronicle.ts 的 interventionOutcome)
    const lostInterventions = rc ? (rc.interventions ?? []).filter((_, i) => !interventionOutcome(rc, i).ok).length : 0;
    // 不起名的这一段里第一笔换上:提示条多一行"地名等点「完成」以后再起"
    const hold = namesHold.current;
    holdTip.current = !rc && !!hold && !hold.tip;
    if (hold && !rc) hold.tip = true;
    setTerrainStatus({ busy: false, last: { ms: rg.arrived, lostNames, lostInterventions } });
    // 编辑地形已经收起了(还没换上就点了「完成」):地图上可以标地名了;没推历史的接着补推
    if (!hold) {
      setNamesHeld(false);
      if (!rc) startNamesRef.current();
    }
  };
  // 重新生成的世界画到地图上以后,记下"从改地形到地图更新"用了多久(冒烟检查用)
  useEffect(() => {
    const rg = regenRef.current;
    if (!rg || rg.arrived === undefined || !data) return;
    const drawn = performance.now() - rg.t0;
    requestAnimationFrame(() => {
      (window as unknown as { __wfTerrain: unknown }).__wfTerrain = {
        id: rg.id,
        ops: rg.terrain.length,
        workerMs: rg.workerMs,
        arrivedMs: rg.arrived,
        drawnMs: drawn,
        paintedMs: performance.now() - rg.t0,
        gotMs: rg.got,
        rasterMs: rg.rasterMs,
        shownMs: rg.shown,
        patch: rg.patch,
      };
    });
    regenRef.current = null;
  }, [data]);

  // ---- 存档(阶段 4):自动存、自动恢复、读档 ----
  useEffect(() => startAutoSave(), []);
  // 建好的世界推完以后,把这次的结果(原件)存进浏览器
  useEffect(() => startResults(), []);
  // AI(阶段 5):登记服务商、恢复设置、调用记录存本地
  useEffect(() => setupAi(), []);
  // 「使用 AI 功能」关了:助手停下、回到现在、收起;正在写的史书停下(写到一半的不存),写史书的窗口、阅读页关上
  const aiOn = useAiOn();
  useEffect(() => {
    if (aiOn) return;
    stopAsk();
    exitPreview();
    closeAssistant();
    stopBook();
    closeHistoryBook();
    closeBookReader();
  }, [aiOn]);
  // 缩略图("我的世界"的卡片、存档菜单):手绘风的地形 480×240;建好的世界叠上结束那一年的国家色块(和正在看哪个图层、哪一年无关)。
  // 地形是结束那一年的(地形大事以后的那一段)。世界还在生成、按新地形重新生成、按新的干预重推历史、那一段的主图还没铺好时 = null,
  // saveStore 过一会儿再来要;编辑地形正涂着(手指、鼠标按着)也先不截。
  // 还没补推历史(编辑地形时生成的):新建中、没有地形大事的不叠国家、地形就是第 0 年的,不再等的那一次(now)照样截
  useEffect(() => {
    setThumbMaker((id, now) => {
      const t = targetRef.current;
      const b = baseRef.current;
      if (!dataRef.current || !b || fresh.current || regenRef.current || resimRef.current || !t || t.id !== id) return null;
      if (!now && terrainStroking()) return null;
      if (civLater.current && !(now && currentWorld()?.kind === 'draft' && !getEdits().upheavals?.length)) return null;
      const kEnd = eraIndex(rawRef.current, null);
      if (!eraReady(eraMapsRef.current, eraPatches.current, kEnd)) return null;
      const d = eraData(b, eraMapsRef.current, eraPatches.current, kEnd);
      // 整张底图先在后台分小步备好(ui/thumbPrep.ts),不在主线程上一口气画
      if (!now && !mapsOf(d).has('fantasy') && !baseReady('fantasy', d.world, d.raster)) return null;
      const rc = rawRef.current;
      const kind = currentWorld()?.kind;
      const cp: CivDrawParams | null =
        kind !== 'draft' && rc && rc.viable && rc.habitat.suitability.length === d.world.mesh.n
          ? { world: d.world, raster: d.raster, civ: rc, style: 'fantasy', year: rc.endYear, show: { ...CIV_SHOW_OFF, polities: true }, thumb: true }
          : null;
      // 国家色块、国界也先在后台分小步备好
      if (!now && cp && !overlayReady(cp.civ, cp.raster, () => civOverlaySteps(cp))) return null;
      const base = baseCanvas('fantasy', d);
      if (!base) return null;
      const cv = document.createElement('canvas');
      cv.width = THUMB_W;
      cv.height = THUMB_H;
      const x = cv.getContext('2d');
      if (!x) return null;
      x.imageSmoothingQuality = 'high';
      x.drawImage(base, 0, 0, cv.width, cv.height);
      if (cp) {
        const ov = document.createElement('canvas');
        ov.width = d.raster.w;
        ov.height = d.raster.h;
        const octx = ov.getContext('2d');
        if (octx) {
          drawCivOverlay(octx, cp);
          x.drawImage(ov, 0, 0, cv.width, cv.height);
        }
        ov.width = ov.height = 0;
      }
      const url = cv.toDataURL('image/jpeg', 0.8);
      cv.width = cv.height = 0;
      return url;
    });
    // 地图缩略图(我的世界的「地图」页签):实景、第 0 年的地形(地形大事以前),不带国界和地名
    setMapThumbMaker((id, now) => {
      const t = targetRef.current;
      const b = baseRef.current;
      if (!b || fresh.current || regenRef.current || !t || t.id !== id) return null;
      if (!now && terrainStroking()) return null;
      if (!now && !mapsOf(b).has('realistic') && !baseReady('realistic', b.world, b.raster)) return null;
      const base = baseCanvas('realistic', b);
      if (!base) return null;
      const cv = document.createElement('canvas');
      cv.width = THUMB_W;
      cv.height = THUMB_H;
      const x = cv.getContext('2d');
      if (!x) return null;
      x.imageSmoothingQuality = 'high';
      x.drawImage(base, 0, 0, cv.width, cv.height);
      const url = cv.toDataURL('image/jpeg', 0.8);
      cv.width = cv.height = 0;
      return url;
    });
    return () => {
      setThumbMaker(null);
      setMapThumbMaker(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // 推演完(重推历史以后也是):结束那一年现存几国记下来,我的世界的卡片上写
  useEffect(() => {
    const cur = currentWorld();
    if (!rawCiv || !cur || cur.kind === 'draft' || cur.id !== targetRef.current?.id || fresh.current) return;
    setWorldStats(aliveAtEnd(rawCiv));
  }, [rawCiv]);
  /**
   * 世界生成完(或要打开的就是正在看的这一个):套上 targetRef 的修改,交给 saveStore 自动存;
   * 核对版本和地形,有问题就提示
   */
  readyRef.current = (world: World, rc: Civ) => {
    lastReady.current = { world, civ: rc };
    const t = targetRef.current;
    if (!t || currentWorld()?.id === t.id) return;
    renameCheck.current = null;
    // 打不开的分享链接(世界还在生成时解开的):现在提示(单独一条,"已恢复"之类的排在它下面,关掉它再露出来)
    const err = shareErr.current;
    shareErr.current = null;
    if (err) showToast({ id: 'share', kind: 'error', text: '打不开这个分享链接', more: [err] });
    /** 提示条上的「看原样」/「到最新版打开」(世界变了样才有,见下面) */
    let act: ToastAction | undefined;
    const say = (n: Parameters<typeof notify>[0]) => n && notify({ ...n, more: n.more?.map((w) => briefWarning(oldSiteNote(w))), action: n.action ?? act });
    const check = worldCheck(world);
    // 投影和中央经线跟着世界存:换成存档里的(旧存档没有 = 等距圆柱、0°)
    if (t.view !== undefined) applyView(t.view ?? undefined);
    // 旧格式的键(r + 州号:GENERATOR_VERSION 2 以前的存档、链接)就地换成按地块的 c 格式,按这一刻的世界解析;
    // 换过的话自动存会写回去(套上的修改和存下的不是同一个对象就会重写)
    const sameT = sameTerrain(t.edits.terrain, genTerrain.current) && sameSketch(t.edits.sketch, genSketch.current);
    const edits = sameT ? upgradeLegacyKeys(t.edits, keySeats(rc.regions)) : t.edits;
    restoredIv.current = edits.interventions;
    restoredUps.current = edits.upheavals;
    // 同一张图换一份修改(打开同种子的另一份存档、分享链接)也算换了世界:正在填的标记、选中的标记作废
    resetMarkUi();
    resetCharacterUi();
    setEdits(edits);
    // 还没存着的旧版本世界(分享链接、旧网址、存不进浏览器的文件):原来那一份跟着(看原样;改了存进来时原样留着)
    const original = t.from === 'url' ? (t.gen !== undefined ? plainSave(world.params, t.gen) : null) : t.from === 'link' || t.from === 'file' ? (t.save ?? null) : null;
    // 照原样打开的旧世界:存档照旧记建它的那一版
    const frozen = frozenLoad.current?.id === t.id ? frozenLoad.current.gen : undefined;
    frozenLoad.current = null;
    // 照原样打开的逐年推演的世界:原件就推到了"现在",不重推,直接停在"现在"
    const fp = civPlay.current;
    if (frozen !== undefined && fp && cleanPlay(edits.play)?.year === fp.year) {
      enterStepwise(playFromOf(edits), fp.year);
      setCivTime({ year: fp.year, playing: false, scrubbing: false, story: false });
    }
    // 在旧版本建的世界的地图上打造文明:现在算出来的地图和它不一样,不让打造(这一份还没存,回到我的世界)
    if (t.kind === 'draft' && t.mapCheck && t.mapCheck !== check) {
      targetRef.current = null;
      showHomeRef.current();
      notify({ kind: 'error', text: '没法在这张地图上打造文明', more: ['这个世界是旧版本做的，地图现在算出来不一样了，没法新开'] });
      return;
    }
    attachWorld({ id: t.id, params: world.params, check, kind: t.kind, title: t.title, saved: t.saved ?? edits, view: t.view ?? undefined, pristine: t.pristine, base: t.base, origin: t.origin, original, frozen });
    if (t.kind !== 'draft') setWorldStats(aliveAtEnd(rc));
    // 分享链接带着"这一刻":画面出来、带着的干预和逐年推演的进度重推完以后,停到那一年、选中、镜头飞过去(见 pendingMoment);
    // 停在某一年就不再自动播放
    if (t.from === 'link' && t.moment) {
      if (t.moment.year !== undefined) takeAutoplay();
      pendingMoment.current = { id: t.id, moment: t.moment };
      // 打开的就是正在看的这张图(地址栏里又贴了一个分享链接):画面不会再变一次,也要停过去
      setMomentTick((n) => n + 1);
    }
    const save = t.save;
    // 刚另存的新版:说一声另存好了(原来那一份照原样留着)
    const copy = savedCopy.current?.id === t.id ? savedCopy.current : null;
    savedCopy.current = null;
    if (copy) {
      // 另存的那份带着要推演的命令时,接着就是"正在重新推演"那条:这条不自动收,推完露出来(右边可以关)
      showToast({ id: 'save', kind: copy.more.length ? 'warn' : 'ok', dot: true, ttl: 0, dismissible: true, text: `已另存为「${t.title ?? ''}」`, more: [`原来的「${copy.from}」照原样留在我的世界里`, ...copy.more] });
      return;
    }
    // 带种子的网址(别人发的普通链接):是旧版本画的就说清现在变了什么
    if (t.from === 'url') {
      const note = t.gen !== undefined ? versionNote(t.gen, false) : null;
      act = versionAction(t.gen !== undefined ? plainSave(world.params, t.gen) : null);
      if (note) say({ kind: 'warn', text: `已打开「种子 ${world.params.seed}」`, more: [note] });
      return;
    }
    if (!save || !t.from) return;
    // 照原样打开的:读档时"来自旧版本…"那句不对了(看到的就是原样)
    const more: string[] = (t.warnings ?? []).filter((w) => frozen === undefined || !w.startsWith('来自旧版本'));
    // 照原样打开的:看到的就是原来的样子,不说"变了什么"、不放「看原样」;同一个世界在这一版网站里只说一次(自动恢复的也说"已打开")
    const told = frozen !== undefined && !toldFrozen(t.id);
    if (told) {
      more.push('这个世界是旧版本建的，照原样打开，新版的改动不影响它');
      // 手机上按钮折成两行(按新版 / 另存一份,phone.css),中间留一个看不见的断点
      act = { label: '按新版\u200b另存一份', act: 'save-new', onClick: () => saveAsNewRef.current() };
    }
    if (frozenBroken.current === t.id) more.push('原样的存档读不出来，按新版打开了');
    frozenBroken.current = null;
    const note = frozen !== undefined ? null : versionNote(save.generator, editedWorld(save.edits));
    // 从文件、分享链接打开的,这句已经在读档的警告里
    if (note && (t.from === 'stored' || t.from === 'restore')) more.push(note);
    // 世界变了样(有"来自旧版本"这一句)才放「看原样」;旧网站里来自更新版本的放「到最新版打开」
    if (note && more.includes(note)) act = versionAction(OLD_SITE !== null ? save : currentOriginal());
    // 地形校验只在"生成时带的地形修改就是存档里的"时才核对
    const cw = sameT ? checkWarning(save, check) : null;
    if (cw) more.push(cw);
    // 改名对不上的:这份历史还要按存档里的干预、地形大事、逐年推演的进度等在后台重推时(地图上先出来的是没带它们的),
    // 改名的人物(和别的重推以后才有的)这会儿还没长出来,不在这里数,重推完按推好的历史再核对(renameCheck)
    const later = sameT && Object.keys(edits.names).length > 0 && historyBehind(edits, getStage().stage === 'draft');
    const lost = later ? 0 : lostRenames(rc, edits.names);
    if (lost) more.push(lostRenamesNote(lost));
    // 文明种子是打造文明时定的,不算"修改"
    const n = editCount(save.edits) - (cleanCivSeed(save.edits.civSeed) !== undefined ? 1 : 0);
    const name = save.title || `种子 ${world.params.seed}`;
    // 提示条第一行。没有要说的就不提示的:没建完的世界接着建、分享的世界(地图下面那条说明已经讲了)、
    // 从我的世界点开的(看到的就是它)、没改过的;从文件打开的、恢复了上次修改的照样说一声
    const text =
      t.kind === 'draft'
        ? `已打开「${name}」`
        : t.from === 'file'
          ? `已打开存档「${name}」${n ? `(改了 ${n} 处)` : ''}`
          : t.from === 'link'
            ? `已打开分享的世界「${name}」`
            : t.from === 'stored' || told || !n
              ? `已打开「${name}」`
              : `已恢复上次的修改(${n} 处)`;
    const always = t.kind !== 'draft' && (t.from === 'file' || (t.from !== 'link' && t.from !== 'stored' && !told && n > 0));
    // 重推完核对出对不上的:同一条提示补上那一句(打开时没提示的,这时提示)
    if (later) renameCheck.current = { id: t.id, terrain: genTerrain.current, show: (line) => say({ kind: 'warn', text, more: [...more, line] }) };
    if (more.length || always) say({ kind: more.length ? 'warn' : 'ok', text, more });
  };
  /** 换成存档里的投影和中央经线(没有 = 等距圆柱、0°;认不出的投影、还没做好的地球仪 = 等距圆柱);存档记了经纬网就换成它的 */
  const applyView = (v: SaveView | undefined) => {
    const want = v?.projection;
    const p: MapProjection = isMapProjection(want) && (want !== 'globe' || GLOBE_READY) ? want : 'equirect';
    const lon = v && Number.isFinite(v.center) ? wrapLon(v.center) : 0;
    if (v?.graticule !== undefined) {
      setGraticule(v.graticule > 0);
      if (isGraticuleStep(v.graticule)) setGraticuleStep(v.graticule);
    }
    if (v?.contours !== undefined) setContourKind(v.contours || null);
    // 先放中心(换投影时按它摆视图),再换投影;等距圆柱再把视图转过去
    publishMapCenter(lon);
    setProjection(p);
    if (!isCurved(p)) requestMapCenter(lon);
  };
  // 投影 / 中心 / 经纬网停下来约半秒:写进网址(刷新、复制网址都还在),已经存着的世界跟着重存一次
  useEffect(() => {
    const t = setTimeout(() => {
      const q = new URLSearchParams(location.search);
      if (projection !== 'equirect') q.set('proj', projection);
      else q.delete('proj');
      q.delete('view'); // 旧的地球仪开关,换成 proj=globe
      if (graticule) q.set('grat', graticule === 30 ? '1' : String(graticule));
      else q.delete('grat');
      if (contourKind) q.set('iso', contourKind);
      else q.delete('iso');
      const lon = Math.round(mapCenter * 100) / 100;
      if (Math.abs(lon) >= 0.005) q.set('lon', String(lon));
      else q.delete('lon');
      const next = `?${q}`;
      if (next !== location.search) navUrl(next);
      viewChanged();
    }, 450);
    return cancelTimeout(t);
  }, [projection, mapCenter, graticule, contourKind]);
  /** 现在这张图(或正在生成的)就是这组参数 + 草图 + 地形修改 */
  const sameGen = (p: WorldParams, terrain: readonly TerrainOp[], sketch: SketchEdit | undefined) =>
    !!genParams.current && worldKey(genParams.current) === worldKey(p) && sameTerrain(terrain, genTerrain.current) && sameSketch(sketch, genSketch.current);
  /**
   * 换到哪一步:新建 / 世界 / 我的世界。进新建时政区、民族换成地形(还没有历史),
   * 离开新建时换回来;选中、概览、改地形属于上一步的,一起收起
   */
  const enterStage = (next: Stage, base: DraftBase | null = null) => {
    const was = getStage().stage;
    if (next !== 'home') closeTrash();
    if (next !== was) {
      clearSelection();
      setPolityPick(null);
      closeOverview();
      setTerrainTool({ on: false });
      closeUpheaval();
      setHover(null);
      clearToast('created');
    }
    // 进新建:默认实景(新建界面的开场就是实景;设过「新建时的默认」就是那个样式);原来的图层记下,不建就离开时换回来
    if (next === 'draft' && was !== 'draft') {
      pausePlayback();
      const { base, fill } = mapViewRef.current;
      // 原来就是卫星也记下:新建里换了别的样式、没建就离开,也换回卫星
      draftViewRef.current ??= { base, fill };
      const first = layerParts(getNewView()?.style ?? 'realistic');
      if (base !== first.base || fill !== 'none') applyMapView({ base: first.base, fill: 'none' });
    }
    if (next !== 'draft' && draftViewRef.current) {
      applyMapView(draftViewRef.current);
      draftViewRef.current = null;
    }
    setStage(next, base);
  };
  /**
   * 打开一个世界:要的就是正在看的这一张图(参数、地形都一样,比如从我的世界打开同一个种子的另一份、以它为底稿新建)就不重新生成,
   * 直接换上它的修改;正在生成的就是它:等生成完;否则按它的参数生成
   */
  const openTarget = (t: Target, step: 'push' | 'replace' = 'push') => {
    // 原来那个世界等着截的缩略图先截下来(同 generate)
    flushThumb();
    const info = navInfo(t.kind === 'draft' ? 'draft' : 'world', t);
    if (step === 'push') navTo(info);
    else navReplace(info);
    setWorldSheet('peek');
    enterStage(t.kind === 'draft' ? 'draft' : 'world', t.kind === 'draft' ? (t.base ?? null) : null);
    if (t.kind === 'draft') setDraftTitle(t.title ?? '');
    setParams(t.params);
    // 照原样打开的旧世界和按新版生成的世界参数一样也不是同一个:都重新打开(旧的读原件;正在找原件、读原件的也不接着用)
    if (sameGen(t.params, t.edits.terrain, t.edits.sketch) && !loadedFrozen.current && !genReq.current && !oldStored(t)) {
      if (fresh.current) {
        targetRef.current = t;
        writeWorldUrl(t);
        return;
      }
      const last = lastReady.current;
      if (!regenRef.current && last && rawRef.current) {
        detachWorld();
        leaveStepwise();
        targetRef.current = t;
        readyRef.current(last.world, rawRef.current);
        writeWorldUrl(t);
        return;
      }
    }
    generate(t);
  };
  /** 打开"我的世界"里的一个(没建完的回到新建) */
  const openStored = (id: string) => {
    const w = loadWorld(id);
    if (!w) return notify({ kind: 'error', text: '打不开这个存档', more: ['可能已在别的页面里删掉了'] });
    // 只存了地图的:不当世界打开,在我的世界的「地图」页签里选中它
    if (w.map) {
      showMapInWorlds(id);
      if (getStage().stage !== 'home') showHome();
      return;
    }
    navTo({ page: w.draft ? 'draft' : 'world', id, seed: w.draft ? w.save.params.seed : undefined, title: w.save.title });
    // 下面一直开着的就是它、存的和开着的一样(没在别的页面里改过):不用重新打开
    const cur = currentWorld();
    const same =
      !!cur &&
      (cur.kind === 'draft') === w.draft &&
      worldKey(cur.params) === worldKey(w.save.params) &&
      (cur.title ?? '') === (w.save.title ?? '') &&
      sameOrigin(cur.origin, w.save.origin) &&
      JSON.stringify(getEdits()) === JSON.stringify(w.save.edits) &&
      // 版本也得一样:开着的是照原样读的旧世界,存着的也得还是那一版;别的页面里换成了别的版本的存档(新版的、旧版的)= 重新打开
      (cur.frozen === undefined || cur.frozen === w.save.generator) &&
      (cur.wrote == null || genOfText(cur.wrote) === w.save.generator);
    if (cur?.id === id && targetRef.current?.id === id && same) {
      markOpened(id);
      enterStage(w.draft ? 'draft' : 'world', w.draft ? (w.base ?? null) : null);
      if (w.draft) setDraftTitle(w.save.title ?? '');
      writeWorldUrl(targetRef.current);
      return;
    }
    openTarget(storedTarget(w, 'stored'));
  };
  /** 从文件打开:存进"我的世界"(算建好的),再打开它;存不下就只打开、不存。「全部存成文件」存的:全部放回我的世界,不打开 */
  const openText = (text: string, fileName?: string) => {
    if (openBundleText(text, fileName)) return;
    const r = parseSave(text);
    if (!r.ok) {
      notify({ kind: 'error', text: fileName ? `打不开 ${fileName}` : '打不开这个存档', more: [briefError(r.error)] });
      return;
    }
    const id = importSave(r.save);
    const w = id ? loadWorld(id) : null;
    const t: Target = w
      ? { ...storedTarget(w, 'stored'), view: r.save.view ?? null }
      : { id: newWorldId(), kind: 'visit', params: r.save.params, edits: r.save.edits, title: r.save.title, view: r.save.view ?? null, save: r.save, origin: r.save.origin ?? null };
    openTarget({ ...t, from: 'file', save: r.save, warnings: r.warnings });
  };
  /**
   * 打开分享链接(解开以后):别人的世界,先不存;改了(或起了名)才存进"我的世界"。
   * 短链接(short):改了另存时写明底稿出处(署名、这时的世界名、这个链接);长链接里没有分享人,不写。
   * own:最新版和旧网站之间交过来的自己的世界:最新版里不出"别人分享给你的世界"那条说明(旧网站上那条换成旧网站的说法,照常出)
   */
  const openShare = (r: ParseResult, short?: { code: string; by?: string; moment?: SaveMoment | null }, own = false) => {
    if (!r.ok) {
      const msg = briefError(r.error);
      // 世界还在生成:等生成完再说(生成时提示条上是进度)
      if (currentWorld()) showToast({ id: 'share', kind: 'error', text: '打不开这个分享链接', more: [msg] });
      else shareErr.current = msg;
      return;
    }
    const sv = r.save;
    const id = newWorldId();
    const by = short ? cleanSignature(short.by) : '';
    setSharedFor(own && OLD_SITE === null ? null : { id, short: !!short, by, own });
    const origin: SaveOrigin | null = short ? { ...(by ? { by } : {}), title: sv.title ?? '', url: shortLink(short.code) } : null;
    // 打开网页时、地址栏里贴的分享链接:浏览器已经记了这一步,换成这个世界
    // 打开时看哪:长链接在存档里(读档时清理过);短链接在链接的 # 后面,按取到的存档再清理一次(年份超出这个世界的历史就不要)
    const moment = sv.moment ?? (short?.moment ? cleanMoment(short.moment, momentYearMax(sv.edits)) : null);
    openTarget({ id, kind: 'visit', params: sv.params, edits: sv.edits, saved: sv.edits, title: sv.title, view: sv.view ?? null, from: 'link', save: sv, warnings: r.warnings, shareCode: short?.code, origin, moment }, 'replace');
  };
  /** 分享短链接:去服务器取存档(不用登录);停了、打不开就显示那一页 */
  const openShortShare = (code: string, still?: () => boolean) => {
    if (!serverBase() || !SHARE_CODE_RE.test(code)) return setLanding('gone');
    showToast({ id: 'share', kind: 'progress', text: '正在打开分享的世界' });
    openShareCode(code)
      .then((r) => {
        // 按后退 / 前进取的:取回来之前又换到了别的画面,不打开(提示条那边换画面时已经收掉了)
        if (still && !still()) return;
        clearToast('share');
        const p = parseSave(JSON.stringify(r.save));
        if (!p.ok) return setLanding({ error: briefError(p.error) });
        setLanding(null);
        // 短链接后面带的"打开时看哪"只在打开网页时那一次用(按后退、前进再取的照平常打开);用了就从地址栏去掉
        const moment = shortMoment.current;
        shortMoment.current = null;
        if (moment && isMomentHash(location.hash)) navUrl(location.pathname + location.search);
        openShareRef.current(p, { code, by: r.by, moment });
      })
      .catch((e) => {
        if (still && !still()) return;
        clearToast('share');
        if (e instanceof ServerError && (e.code === 'share-gone' || e.code === 'not-found')) setLanding('gone');
        else setLanding({ error: e instanceof ServerError && e.code === 'network' ? '连不上服务器，请检查网络后刷新再试。' : e instanceof Error ? e.message : String(e) });
      });
  };
  const openShareRef = useRef(openShare);
  openShareRef.current = openShare;
  /** 打开网页时短链接后面带的"打开时看哪"(取到存档时用掉) */
  const shortMoment = useRef<SaveMoment | null>(init.moment);
  /** 朋友的预设链接解开以后:选上分享来的那一套(不存);打不开的说一声(照常停在我的世界),有个别参数不对的也说一声 */
  const presetOpened = (r: PresetLinkResult) => {
    if (!r.ok) return notify({ kind: 'error', text: '打不开这个预设链接', more: [r.error] });
    pickSharedPreset(r.preset);
    if (r.warnings.length) notify({ kind: 'warn', text: `已打开朋友分享的预设「${r.preset.name}」`, more: r.warnings });
  };
  /** 换到作品墙的一页(盖在我的世界的位置上):停下正在放的,网址换成作品墙的 */
  const enterWall = (v: WallView, id: string) => {
    wallSeq.current++;
    pausePlayback();
    setReplayOn(false);
    setLanding(null);
    setWorkFor(null);
    enterStage('home');
    setWall(v);
    writeGalleryUrl(id);
  };
  /** 去作品墙那一页(我的世界右上、空页面的精选、作品左上的「‹ 作品墙」、撤下了的那一页) */
  const showGallery = () => {
    navTo({ page: 'gallery' });
    enterWall({ kind: 'list' }, '');
  };
  /**
   * 打开作品墙上的一个作品(作品墙上点的、我的世界空页面上的精选、作品的网址):先是一页空白,去服务器取;
   * 世界作品打开那个世界(只是看看),地图作品整屏一颗星球,新建参数作品在作品墙那一页上弹窗;撤下了、没有这个编号整页说"已经撤下了"
   */
  const openWork = (id: string) => {
    navTo({ page: 'gallery', id });
    enterWall({ kind: 'work', id, state: 'loading' }, id);
    const my = wallSeq.current;
    if (!isWorkId(id) || !serverBase()) return setWall({ kind: 'work', id, state: 'gone' });
    fetchWork(id).then(
      (it) => {
        if (my !== wallSeq.current) return;
        if (it.kind === 'world') return openWorkWorld(it);
        setWall(it.kind === 'map' ? { kind: 'map', work: it } : { kind: 'list', preset: it });
      },
      (e: unknown) => {
        if (my !== wallSeq.current) return;
        const gone = isWorkGone(e);
        setWall({ kind: 'work', id, state: gone ? 'gone' : { error: e instanceof ServerError && e.code === 'network' ? '连不上服务器，请检查网络后再试。' : e instanceof Error ? e.message : String(e) } });
        // 作品墙上的卡片跟着去掉
        if (gone) loadGallery(true);
      },
    );
  };
  /** 打开世界作品:和打开分享链接一样,别人的世界先只是看看,改了才另存进我的世界(出处写作品) */
  const openWorkWorld = (it: GalleryItem) => {
    const p = parseSave(JSON.stringify(it.save ?? null));
    if (!p.ok) return setWall({ kind: 'work', id: it.id, state: { error: briefError(p.error) } });
    const sv = p.save;
    const id = newWorldId();
    setWall(null);
    setSharedFor(null);
    setWorkFor({ id, work: it });
    workItems.current.set(id, it);
    openTarget(
      { id, kind: 'visit', params: sv.params, edits: sv.edits, saved: sv.edits, title: it.title || sv.title, view: sv.view ?? null, from: 'link', save: sv, warnings: p.warnings, gallery: it.id, origin: workOrigin(it), moment: sv.moment ?? null },
      'replace',
    );
  };
  /** 世界作品「另存一份接着改」:存进我的世界(出处已经写着),网址换成它的编号 */
  const keepWork = () => {
    const c = currentWorld();
    const t = targetRef.current;
    if (!c || !t || !workFor || c.id !== workFor.id) return;
    if (c.kind === 'visit') keepWorld(c.id);
    if (!isStored(c.id)) return notify({ kind: 'error', text: '没能另存', more: [storageFullWhy()] });
    writeWorldUrl(t);
    showToast({ id: 'save', kind: 'ok', text: `已存进我的世界「${c.title || workFor.work.title || '未命名世界'}」`, more: [`出处写着${workWho(workFor.work)}`] });
  };
  /** 新建参数作品「用这套参数新建」:回到我的世界,新建弹窗第 2 步照它填好(不自动存进自己的预设) */
  const takePresetWork = (p: SharedPreset) => {
    showHome();
    pickSharedPreset(p);
    setNewDlg({ ...presetDialog(p), stamp: performance.now() });
  };
  const wallRef = useRef({ open: openWork, list: showGallery });
  wallRef.current = { open: openWork, list: showGallery };
  /** 新建世界(我的世界右上、第一次来、分享停了的那一页):先弹窗选怎么生成、定基础参数 */
  const startDraft = () => setNewDlg({});
  /** 弹窗里点了「取消」:什么都不留下(刷新回来的照图新建,网址里的 new=image 也去掉,再刷新不再弹) */
  const cancelDialog = () => {
    setNewDlg(null);
    writeHomeUrl();
  };
  /**
   * 弹窗里点了「开始」:存下没建完的世界、进新建界面。照手绘图的把读好的图交过去,进去直接是第 1 步「认出海陆」
   * (照手绘图的新建界面一进来就打开改地形工具,认图在它上面)
   */
  const startFromDialog = (s: NewWorldStart) => {
    // 作品墙上新建参数作品「用这套参数新建」打开的弹窗:新的世界出处写这个作品(和另存世界作品一样);换成了别的预设就不写
    const g = chosenGallery(getPresets(), newDlg?.shared);
    setNewDlg(null);
    const plain = draftTarget(s.params, null, yearsEdits(s.endYear, s.frontier));
    const d = g?.id && isWorkId(g.id) ? { ...plain, origin: workOrigin({ id: g.id, by: g.by, title: g.title ?? '' }) } : plain;
    if (s.mode === 'random') return openTarget(d);
    openTarget({ ...d, mode: 'image' });
    if (s.picture) beginImport(s.picture);
  };
  /** 新建中的世界(在看的就是它)*/
  const draftNow = (): Target | null => {
    const t = targetRef.current;
    return t && t.kind === 'draft' && getStage().stage === 'draft' ? t : null;
  };
  /** 新建中:最新的名字、动没动过(存在 saveStore 里;还在生成时看 targetRef) */
  const draftState = (t: Target) => {
    const cur = currentWorld();
    const attached = cur?.id === t.id;
    return { title: attached ? cur.title : t.title, pristine: attached ? cur.pristine : t.pristine, edits: attached ? getEdits() : t.edits };
  };
  /** 新建中换种子:另一颗星球,草图留着(连同放的火山湖河);没画草图时放的那几处作废;没起名、参数也是默认的、没画草图 = 又算没动过(不存) */
  const draftSeed = (seed: number, params?: WorldParams) => {
    const t = draftNow();
    // 以别的世界为底稿、在一张地图上打造文明:种子锁着
    if (!t || t.base || t.edits.map) return;
    const st = draftState(t);
    // 按后退 / 前进换回的那颗:参数也换回那一步的(params)
    const base = params ?? t.params;
    // 换一颗:草图带过去,照它长出新的山河;陆地海洋是照草图长的,放的火山湖河也还对得上,一起带过去。
    // 没画草图 = 整颗星球都换了,放的那几处是照原来的地形放的,不带过去。助手的对话(说的是原来那颗)也清掉
    newConversation();
    const sketch = st.edits.sketch;
    const plain =
      !st.title &&
      !sketch &&
      !st.edits.nameMix &&
      !st.edits.endYear &&
      !st.edits.frontier &&
      !st.edits.calamity &&
      !st.edits.origins &&
      st.edits.civSeed === undefined &&
      !st.edits.era &&
      st.edits.months === undefined &&
      worldKey({ ...base, seed: 0 }) === worldKey({ ...DEFAULT_PARAMS, seed: 0 });
    // 地名风格、推演年数、拓荒和参数一样是这一类星球的设定,换一颗照旧;选的起源按位置照旧(新星球上那里住不了人的,推演时跳过);
    // 纪年、月份(年份的写法)也照旧,按一件事定的换成按年份(那件事是原来那颗星球上的)
    const { nameMix, endYear, frontier, calamity, origins, civSeed, era, months } = st.edits;
    const kept: WorldEdits = sketch ? { ...EMPTY_EDITS, sketch, terrain: st.edits.terrain } : EMPTY_EDITS;
    const edits = {
      ...kept,
      ...(nameMix ? { nameMix } : {}),
      ...(endYear ? { endYear } : {}),
      ...(frontier ? { frontier } : {}),
      ...(calamity ? { calamity } : {}),
      ...(origins ? { origins } : {}),
      ...(civSeed !== undefined ? { civSeed } : {}),
      ...(era ? { era: { name: era.name, epoch: era.epoch } } : {}),
      ...(months !== undefined ? { months } : {}),
    };
    // 换一颗:记一步(按后退换回刚才那颗)
    navTo({ page: 'draft', id: t.id, seed, title: st.title });
    generate({ ...t, params: { ...base, seed }, edits, saved: undefined, title: st.title, pristine: st.pristine || plain, view: undefined, from: undefined, save: undefined });
  };
  /** 新建中调参数:改过的地形留着(按新参数重新生成) */
  const draftParams = (p: WorldParams) => {
    const t = draftNow();
    // 在一张地图上打造文明:地图锁着
    if (!t || t.edits.map) return;
    const st = draftState(t);
    generate({ ...t, params: { ...p, seed: t.base ? t.params.seed : p.seed }, edits: st.edits, saved: undefined, title: st.title, pristine: false, view: undefined, from: undefined, save: undefined });
  };
  /** 新建中起名(点别处 / 回车):起了名就算动过,存进我的世界("没建完") */
  const draftRename = (title: string) => {
    const t = draftNow();
    if (!t) return;
    const clean = cleanTitle(title) || undefined;
    t.title = clean;
    setDraftTitle(clean ?? '');
    if (currentWorld()?.id === t.id) renameWorld(t.id, clean ?? '');
    // 星球还在生成:同样算动过(生成好了照这个名字存下;这时按后退离开,回来名字也还在)
    else t.pristine = false;
  };
  /**
   * 创建世界:从此种子、参数、地形锁住;一直存着。从第 0 年起放一遍历史;how = 新建时选了「演绎」(step):从第 0 年起逐年推演、马上往下走;
   * 选了「照大纲」(outline):不放历史,打开概览的「大纲」页先写大纲。建成了 = true
   */
  const createWorld = (title: string, how?: 'step' | 'outline', stopAt?: number): boolean => {
    const t = draftNow();
    const cur = currentWorld();
    // 还在生成、在重推带过来的干预、在放这颗星球的形成:等它完
    if (!t || !cur || cur.id !== t.id || fresh.current || regenRef.current || civLater.current || resim || replayOn) return false;
    const clean = cleanTitle(title) || undefined;
    if ((clean ?? '') !== (cur.title ?? '')) renameWorld(t.id, clean ?? '');
    // 记成预设里的「上次用的」(不含种子)
    rememberLast(t.params, cleanEndYear(getEdits().endYear), clean ?? '');
    // 说存住了,要真的写进了浏览器(存储满了、删了旧的也写不下,或者浏览器不让存 = 只在这一页里)
    const stored = markCreated() && persistent();
    // 新建时执行过的改地形从此不能再撤销:⌘Z 也不再往回退(助手那边按锁换了,旧的确认单不能执行)
    clearEditHistory();
    // 地形锁住了:后台线程为编辑地形留着的整图放掉(没有回音,不算一件活)
    workerRef.current?.postMessage({ type: 'release', id: 0 } satisfies WorkerRequest);
    targetRef.current = { ...t, kind: 'created', base: null, pristine: false, title: clean, from: undefined, save: undefined };
    // 这一步换成建好的世界;前面换过的几颗星球(同一个编号)按后退时跳过(见 routeNav)
    navReplace({ page: 'world', id: t.id, title: clean });
    enterStage('world');
    // 建好的世界看政区
    draftViewRef.current = null;
    applyLayer('political');
    writeWorldUrl(targetRef.current);
    if (rawRef.current) setWorldStats(aliveAtEnd(rawRef.current));
    refreshThumb();
    const keep = persistent();
    showToast({
      id: 'created',
      kind: stored ? 'ok' : 'warn',
      dot: stored,
      text: `${clean ?? '新世界'}已创建`,
      more: [stored ? '自动存在这个浏览器里，在「我的世界」里随时能找到' : keep ? `${storageFullWhy()}，没能存下；关掉页面前请存成文件` : '浏览器不让网页存数据，关掉页面前请存成文件'],
      ttl: 7000,
    });
    // 历史从第 0 年起放一遍(这次打开网页不再另外自动播放);不放(play=0、无头浏览器)时,
    // 新建时放过"这颗星球的形成"、时间停在第 0 年的,回到结束那一年。
    // 推得比 3000 年久的世界:新建时只推了 3000 年,创建以后接着往后推(重推那段),推完再放;调了拓荒、选了起源的同样创建以后重推
    takeAutoplay();
    // 选了「演绎」:换成从第 0 年起逐年推演(推到第 0 年年初就停,接着一步步往下走),不放一遍历史
    if (how === 'step') {
      storyAfterYears.current = null;
      stepAuto.current = true;
      putEditsQuiet(startStepwise(getEdits(), 0));
      return true;
    }
    const later = cleanEndYear(getEdits().endYear) !== civYears.current || !sameSetup(setupFor(false, getEdits()), civSetup.current);
    // 照故事找的:停在开场那年,不从第 0 年放(推得更久的接着推完也不放);选了照大纲的照样先打开大纲
    if (stopAt !== undefined) {
      storyAfterYears.current = null;
      setCivTime({ year: stopAt, playing: false, scrubbing: false, story: false });
      if (how === 'outline') openOverview('outline');
      return true;
    }
    if (how === 'outline') {
      openOverview('outline');
      if (getCivTime().year === 0) resetCivTime();
      return true;
    }
    if (later) storyAfterYears.current = storyOk();
    if (storyOk() && !later) startCivReplay();
    else if (getCivTime().year === 0) resetCivTime();
    return true;
  };
  /**
   * 以正在看的世界为底稿新建:设定、改名、干预都带过去(还是这张图,不用重新生成);存成另一个世界。
   * 带着东西、起好了名,一开始就存(作为没建完的,刷新不丢);什么都没动就点返回,这一份删掉
   */
  const draftFromCurrent = () => {
    const t = targetRef.current;
    const cur = currentWorld();
    if (!t || !cur || cur.id !== t.id || fresh.current) return;
    // 以它为底稿新建的地图还能改:不再算原来那张地图上的(地图记录不带;文明种子照旧带过去)
    const orig = getEdits();
    const e: WorldEdits = { ...orig };
    delete e.map;
    const base: DraftBase = { id: cur.id, title: cur.title || '未命名世界', names: Object.keys(e.names).length, interventions: e.interventions.length };
    backRef.current = { ...t, kind: cur.kind, edits: orig, saved: undefined, title: cur.title, from: undefined, save: undefined, view: undefined };
    const d = draftTarget(t.params, base, e, nextTitle(base.title));
    derivedRef.current = { id: d.id, sig: draftSig(d.params, d.edits, d.title) };
    openTarget({ ...d, pristine: false, view: undefined });
  };
  /** 新建第 1 步点了「保存地图」:只存地图(没有文明),回到我的世界的「地图」页签、选中它。存下了 = true */
  const saveMap = (): boolean => {
    // 编辑地形时没起的地名接着在后台起(不等它)
    releaseNames();
    const t = draftNow();
    const cur = currentWorld();
    if (!t || !cur || cur.id !== t.id || fresh.current || regenRef.current) return false;
    if (!saveCurrentAsMap()) {
      notify({ kind: 'error', text: '没能保存地图', more: [persistent() ? storageFullWhy() : '浏览器不让网页存数据'] });
      return false;
    }
    showMapInWorlds(t.id);
    showHome();
    return true;
  };
  /**
   * 在一个世界(或只存了地图的那一份)的地图上打造新文明:进新建界面的「打造文明」(地图锁着,定文明种子、推演年数、拓荒、起源、
   * 名字、地名风格)。用的是它一开始的地图(参数、地形修改、草图;不带地形大事),原来的国家、人物、干预、改名……都不带;原来的不动。
   * 文明种子先随机给一个;名字先填"原名(二)"。旧版本建的世界:生成出来的地图和它存的对不上就不让打造(见 readyRef)
   */
  const startNewCiv = (id: string) => {
    const w = loadWorld(id);
    if (!w || w.draft) return notify({ kind: 'error', text: '打不开这张地图', more: ['可能已在别的页面里删掉了'] });
    newCivOn(w.save, id, w.map ? undefined : nextTitle(w.save.title || '未命名世界'), w.save.origin ?? null);
  };
  /**
   * 在一份存档的地图上打造新文明(见 startNewCiv)。from = 地图出自哪(我的世界里的编号;作品墙上的作品是 gallery:<作品编号>),
   * 同一张地图上打造的文明在我的世界的「地图」里排在一起
   */
  const newCivOn = (save: SaveFile, from: string, title: string | undefined, origin: SaveOrigin | null) => {
    const edits = newHistoryEdits(save.edits, { civSeed: randomSeedValue(), from, sum: save.edits.map?.sum });
    const mapCheck = save.generator < GENERATOR_VERSION && save.check ? save.check : undefined;
    setNewDlg(null);
    // 一开始就存成没建完的(刷新、后退再前进都回得来;地图出自哪个世界、文明种子都在存档里),底稿出处跟着;什么都没动就返回,这一份删掉
    const d = draftTarget(save.params, null, edits, title);
    derivedRef.current = { id: d.id, sig: draftSig(d.params, d.edits, d.title) };
    openTarget({ ...d, pristine: false, origin, mapCheck });
  };
  /** 作品墙上的世界 / 地图作品「用这张地图打造(新)文明」:地形照搬,文明和历史从头推演;出处写作品 */
  const newCivOnWork = (it: GalleryItem) => {
    const p = parseSave(JSON.stringify(it.save ?? null));
    if (!p.ok) return notify({ kind: 'error', text: '打不开这张地图', more: [briefError(p.error)] });
    setWall(null);
    setWorkFor(null);
    newCivOn(p.save, `gallery:${it.id}`, it.kind === 'map' ? undefined : nextTitle(it.title || p.save.title || '未命名世界'), workOrigin(it));
  };
  const startNewCivRef = useRef(startNewCiv);
  startNewCivRef.current = startNewCiv;
  useEffect(() => {
    setNewCivHandler((id) => startNewCivRef.current(id));
    setOpenWorldHandler((id) => openStoredRef.current(id));
    return () => {
      setNewCivHandler(null);
      setOpenWorldHandler(null);
    };
  }, []);
  // 先出来的首页上点的那一件(主程序那时还在下载):挂上以后接着做,和在这里点的一样(浏览器的后退已经在上面接上了)
  useEffect(() => {
    const s = fromHome;
    if (!s) return;
    if (s.kind === 'open') openStored(s.id);
    else if (s.kind === 'text') openText(s.text, s.fileName);
    else if (s.kind === 'newCiv') startNewCiv(s.id);
    // 作品墙那一页、作品:首页上已经把网址换成了它,上面照网址已经打开了(再开一次会把开着的新建参数作品关掉、多取一次)
    else if (s.kind === 'gallery') {
      if (init.gallery === null) showGallery();
    } else if (s.kind === 'work') {
      if (init.gallery !== s.id) openWork(s.id);
    }
    else if (s.kind === 'preset') takePresetWork(s.preset);
    else startFromDialog(s.start);
    // 只在挂上时做一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  /** 以别的世界为底稿新建时,那个世界(没存过的也回得去) */
  const backRef = useRef<Target | null>(null);
  /** 以别的世界为底稿新建的那一份:编号和一开始的样子(返回时没动过就删掉) */
  const derivedRef = useRef<{ id: string; sig: string } | null>(null);
  /** 以底稿新建的那一份还是一开始的样子(参数、修改、名字都没动) */
  const derivedUntouched = (): string | null => {
    const d = derivedRef.current;
    const t = targetRef.current;
    const cur = currentWorld();
    if (!d || !t || !cur || t.id !== d.id || cur.id !== d.id) return null;
    return draftSig(t.params, getEdits(), cur.title) === d.sig ? d.id : null;
  };
  /** 回到"我的世界"(一个都没有时是空的那一页) */
  const showHome = () => {
    navTo({ page: 'home' });
    pausePlayback();
    setReplayOn(false);
    enterStage('home');
    wallSeq.current++;
    setWall(null);
    setWorkFor(null);
    writeHomeUrl();
  };
  const goHome = showHome;
  const showHomeRef = useRef(showHome);
  showHomeRef.current = showHome;
  const openStoredRef = useRef(openStored);
  openStoredRef.current = openStored;
  /**
   * 照原样打开的旧世界「按新版另存一份」(提示条、存档菜单、推演前问的窗口):原来的不动,另存一份带着 edits(不给 = 现在的修改),
   * 打开它按新版重新生成、推演;AI 写的史书、名字由来跟着复制
   */
  const saveAsNewNow = (edits?: WorldEdits) => {
    closeSaveAsNew();
    const c = currentWorld();
    if (!c || c.frozen === undefined) return;
    const from = c.title || `种子 ${c.params.seed}`;
    const id = saveAsNewVersion(c.id, edits ?? getEdits());
    if (!id) return notify({ kind: 'error', text: '没能另存', more: [storageFullWhy()] });
    const more = copyNotes(c.id, id) ? [] : ['AI 写的史书、名字由来没能一起存下（浏览器存储已满）'];
    savedCopy.current = { id, from, more };
    openStoredRef.current(id);
  };
  const saveAsNewRef = useRef(saveAsNewNow);
  saveAsNewRef.current = saveAsNewNow;
  useEffect(() => {
    setSaveAsNew((e) => saveAsNewRef.current(e));
    // 照原样打开的旧世界:改历史(要用现在的规则重新推演)先问要不要另存一份;别的世界照常改。
    // 逐年推演:只能在"现在"干预(下一步生效),不改以前的历史(撤销、助手执行的都算);想改以前的事先存回推演模式
    setHistoryGate((next) => {
      if (cleanPlay(getEdits().play) && cleanPlay(next.play)) {
        showToast({ id: 'edit-block', kind: 'warn', text: '逐年推演里只能在「现在」干预', more: ['想改以前的事，先存回推演模式'], ttl: 5000 });
        return true;
      }
      const c = currentWorld();
      if (!c || c.frozen === undefined) return false;
      const now = getEdits();
      const count = Math.max(0, next.interventions.length - now.interventions.length) + Math.max(0, (next.upheavals?.length ?? 0) - (now.upheavals?.length ?? 0));
      askSaveAsNew({ next, title: c.title || `种子 ${c.params.seed}`, count });
      return true;
    });
    return () => {
      setSaveAsNew(null);
      setHistoryGate(null);
    };
  }, []);
  // 云同步:登录了就开始(account/sync.ts);正在看的世界在别的设备上、别的页面里改过,点"载入"重新打开它;账号窗里点"最近删除"回到我的世界
  useEffect(() => {
    const stop = startSync();
    setReloadHandler((id) => openStoredRef.current(id));
    setReopenHandler((id) => openStoredRef.current(id));
    setGoHome(() => {
      if (getStage().stage !== 'home') showHomeRef.current();
    });
    return () => {
      stop();
      setReloadHandler(null);
      setReopenHandler(null);
      setGoHome(null);
    };
  }, []);
  const v = useSavesVersion();
  // 正在看的世界改了名:浏览器记的这一步也换成新名字
  useEffect(() => {
    const cw = currentWorld();
    if (cw) navTitle(cw.id, cw.title || undefined);
  }, [v]);
  /**
   * 新建卡片左上的返回:底稿那个世界 / 我的世界;第一次来(没有别的世界)不显示。
   * 每次渲染现做(不 useMemo):记下来的回调会连带拉住记下那一刻的世界,编辑地形涂了几笔以后旧的主图还放不掉
   */
  const draftBack = (() => {
    if (!draft) return null;
    if (stageBase) {
      return {
        label: stageBase.title,
        onClick: () => {
          const b = backRef.current;
          const left = derivedUntouched();
          if (left) deleteWorld(left);
          // 前一步就是那个世界:退回去(和浏览器的后退一样,不多记一步)
          if (navBack({ page: 'world', id: stageBase.id })) return;
          if (isStored(stageBase.id)) openStored(stageBase.id);
          else if (b && b.id === stageBase.id) openTarget(b);
          else goHome();
        },
      };
    }
    return {
      label: '我的世界',
      onClick: () => {
        if (navBack({ page: 'home' })) return;
        // 在一张地图上打造、什么都没动就返回:那一份删掉(后退的话 routeNav 删)
        const left = derivedUntouched();
        if (left) deleteWorld(left);
        goHome();
      },
    };
  })();
  // ---- 照故事找世界(FinderPage.tsx;条件、结果在 finderStore.ts) ----
  // 新建世界第 1 步点「照故事找世界」进去:新建界面收起,平常的地图露出来(手绘、国家);选中一个结果,新建中的世界换成那个世界
  // (地图、文明种子照搜的时候的),停在开场那年,两国描边、交界那州圈出来;「用这个世界」回到新建第 2 步(那几样设定锁着);
  // 「‹ 新建世界」离开时新建中的世界换回原来的样子
  /** 打开找世界那一页时:新建中的世界原来的样子、地图原来的样式(新建界面的)、搜的时候照它生成的设定 */
  const finderBack = useRef<{ target: Target; view: { base: BaseId; fill: FillId }; base: FinderBase; moved: boolean } | null>(null);
  /** 「用这个世界」以后:新建第 2 步锁着的那几样、建好以后停在哪年、加哪几个标记(从大纲页来的:搬哪份大纲) */
  const [found, setFound] = useState<(StudioFound & { pick: FoundPick; pts: [number, number][]; gen: string; from?: OutlineFrom }) | null>(null);
  /**
   * 从大纲页「找更合的世界」进来的:原来那个世界的大纲(建好以后搬过去,outlineMove.ts)、点之前地图的样式;
   * 找世界那一页的「‹ 大纲」回原来那个世界的大纲
   */
  const [outlineSrc, setOutlineSrc] = useState<{ from: OutlineFrom; view: { base: BaseId; fill: FillId } } | null>(null);
  /** 一张地图认是不是同一张:参数、地形、草图(在哪张地图上打造的那条出处不算:地图本身一样) */
  const mapKeyOf = (p: WorldParams, e: WorldEdits) => JSON.stringify([worldKey(p), e.terrain, e.sketch ?? null]);
  /** 新建中的世界 → 搜的时候照它生成的设定(世界参数、地形和草图(都用这张地图时)、推演年数、拓荒、起源、天灾、地名风格) */
  const finderBaseOf = (t: Target, e: WorldEdits): FinderBase => {
    const endYear = cleanEndYear(e.endYear);
    const frontier = cleanFrontier(e.frontier);
    const origins = cleanOrigins(e.origins);
    const calamity = cleanCalamity(e.calamity);
    const civ = { ...(endYear ? { endYear } : {}), ...(frontier ? { frontier } : {}), ...(origins ? { origins } : {}), ...(calamity ? { calamity } : {}), ...(e.nameMix ? { names: e.nameMix } : {}) };
    const sketch = sketchGrid(e.sketch);
    return {
      key: JSON.stringify([worldKey(t.params), e.terrain, e.sketch ?? null, civ]),
      setup: { world: t.params, ...(Object.keys(civ).length ? { civ } : {}), ...(e.terrain.length ? { terrain: [...e.terrain] } : {}), ...(sketch ? { sketch } : {}) },
    };
  };
  /** 新建第 1 步点「照故事找世界」(again:「用这个世界」以后点「回去换一个」,回到上次的结果) */
  const openFinderPage = (again = false) => {
    // 新建中的世界还在生成也能进(「再找」新建的那一个):地图生成好了再露出来
    const t = draftNow();
    if (!t) return;
    if (!again || !finderBack.current) {
      const st = draftState(t);
      const back: Target = { ...t, edits: st.edits, title: st.title, pristine: st.pristine, saved: undefined, view: undefined, from: undefined, save: undefined };
      finderBack.current = { target: back, view: { base: mapViewRef.current.base, fill: mapViewRef.current.fill }, base: finderBaseOf(t, st.edits), moved: false };
    }
    setTerrainTool({ on: false });
    closeAssistant();
    // 新建界面收起时,投影、经纬网先留着(回来接着用;离开新建时再换回进新建之前的)
    carryStudioView();
    applyMapView({ base: 'fantasy', fill: 'polities' });
    if (!again) setCivTime({ year: null, playing: false, scrubbing: false, story: false });
    openFinder(finderBack.current.base, narrowRef.current);
  };
  /** 选中的一个结果:新建中的世界换成它(地图种子 = 它,或者都用这张地图、只换文明种子);已经是它就不动 */
  const finderPreview = (seed: number) => {
    const back = finderBack.current;
    const t = draftNow();
    const run = getFinder().run;
    if (!back || !t || !run) return;
    const fixed = run.setup.map === 'fixed';
    const be = back.target.edits;
    const params = fixed ? back.target.params : { ...back.target.params, seed };
    const { nameMix, endYear, frontier, origins, calamity, era, months } = be;
    const keep: Partial<WorldEdits> = {
      ...(nameMix ? { nameMix } : {}),
      ...(endYear ? { endYear } : {}),
      ...(frontier ? { frontier } : {}),
      ...(origins ? { origins } : {}),
      ...(calamity ? { calamity } : {}),
      ...(era ? { era } : {}),
      ...(months !== undefined ? { months } : {}),
    };
    // 都用这张地图:文明种子照搜的时候明写(和地图种子一样也写:改过地形的地图上,写没写推出来的不一样)
    const edits: WorldEdits = fixed ? { ...be, civSeed: seed } : { ...EMPTY_EDITS, ...keep };
    const cur = targetRef.current;
    if (cur?.fullCiv && genParams.current && worldKey(genParams.current) === worldKey(params) && cleanCivSeed(cur.edits.civSeed) === cleanCivSeed(edits.civSeed)) return;
    back.moved = true;
    generate({ ...t, params, edits, saved: undefined, title: back.target.title, pristine: back.target.pristine, view: undefined, from: undefined, save: undefined, fullCiv: true });
  };
  /** 「‹ 新建世界」:新建中的世界换回原来的样子,地图换回新建界面的样式;从大纲页来的「‹ 大纲」回原来那个世界的大纲 */
  const exitFinder = () => {
    const back = finderBack.current;
    const src = outlineSrc;
    finderBack.current = null;
    closeFinder();
    selectFinder(null);
    setCivHighlight(null);
    setFound(null);
    setOutlineSrc(null);
    if (src && isStored(src.from.world)) {
      applyMapView(src.view);
      openStored(src.from.world);
      openOverview('outline');
      return;
    }
    if (!back) return;
    applyMapView(back.view);
    if (back.moved && draftNow()) generate({ ...back.target });
  };
  /** 找世界那一页上选中的结果、那种配法 */
  const finderSum = useMemo(
    () => (finderOn && finder.run ? summarize(finder.run.query, finder.run.reports, finder.variant, finder.sort) : null),
    [finderOn, finder.run?.query, finder.run?.reports, finder.variant, finder.sort], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const finderPick = useMemo(() => (finderSum ? pickedOf([...finderSum.full, ...finderSum.near], finder.sel) : null), [finderSum, finder.sel]);
  /** 选中的那个世界生成好了(地图和文明种子对得上):地图上贴小牌子、写名字用 */
  const finderPreviewData: FinderPreview | null = (() => {
    const back = finderBack.current;
    if (!finderOn || !finderPick || !back || !data || !rawCiv || !realCiv || progress || !targetRef.current?.fullCiv) return null;
    const seed = finderPick.row.seed;
    const fixed = finder.run?.setup.map === 'fixed';
    if (rawCiv.seed !== seed || data.world.params.seed !== (fixed ? back.target.params.seed : seed)) return null;
    return { seed, world: data.world, civ: realCiv };
  })();
  // 选中了就换过去(还在生成上一个也换:后台只认最新的)
  useEffect(() => {
    if (finderOn && finder.sel) finderPreview(finder.sel.seed);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finderOn, finder.sel?.seed]);
  // 搜完了还没选:选上最合的那个(没有全合的选差一条里最近的)
  const finderDone = finder.run?.progress?.state === 'done';
  useEffect(() => {
    const first = finderSum?.full[0] ?? finderSum?.near[0];
    if (!finderOn || !finderDone || getFinder().sel || !first) return;
    selectFinder({ seed: first.seed, alt: -1 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finderOn, finderDone]);
  /** 生成好了:停在开场那年,两国描边、交界那州圈出来,地图飞过去看全两国(同一个结果只飞一次) */
  const finderShown = useRef('');
  const finderPreviewKey = finderPreviewData && finderPick ? `${finderPick.row.seed}:${finderPick.cand.year}:${finderPick.cand.roles.join(',')}:${finder.variant}` : '';
  useEffect(() => {
    if (!finderPreviewKey || !finderPreviewData || !finderPick) return;
    const { cand, places } = finderPick;
    setCivTime({ year: cand.year, playing: false, scrubbing: false, story: false });
    setCivShow({ polities: true });
    const junction = places.filter((p) => p.kind === 'junction').map((p) => p.region);
    setCivHighlight({ regions: junction, polities: cand.roles, year: cand.year, steady: true });
    if (finderShown.current === finderPreviewKey) return;
    finderShown.current = finderPreviewKey;
    flyToPoints(storyPoints(finderPreviewData.world, finderPreviewData.civ, cand, places), 'finder');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finderPreviewKey]);
  // 点开一个结果的细节:地图再放大到故事里最小的那一国和隘口、交界(两国里多半是要守的那一个)
  const finderDetail = finderOn && finder.page === 'detail';
  useEffect(() => {
    if (!finderDetail || !finderPreviewData || !finderPick) return;
    const { cand, places } = finderPick;
    const near = places.filter((p) => p.kind !== 'port');
    let small = 0;
    cand.sizes.forEach((s, i) => s < cand.sizes[small] && (small = i));
    const one = cand.roles.length ? { ...cand, roles: [cand.roles[small]], capitals: cand.capitals.slice(small, small + 1) } : cand;
    flyToPoints(storyPoints(finderPreviewData.world, finderPreviewData.civ, one, near), 'finder');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finderDetail, finderPreviewKey]);
  // 离开新建(回我的世界、打开别的世界):找世界那一页收起,结果不要了
  useEffect(() => {
    if (draft) return;
    finderBack.current = null;
    setFound(null);
    setOutlineSrc(null);
    if (getFinder().open || getFinder().run) resetFinder();
    // 新建界面收起着(在找世界那一页)就离开了新建:进新建之前的投影、经纬网换回来(平常是新建界面卸下时自己换)
    const c = takeStudioView();
    if (c) {
      if (c.proj !== 'equirect' && getProjection() === 'equirect') setProjection(c.proj, c.flat);
      setGraticule(c.grat.on);
      setGraticuleStep(c.grat.step);
    }
  }, [draft]);
  /** 「谁是谁」点一行:地图飞到那一国 / 那一处 */
  const finderFly = (to: FinderFlyTo) => {
    const pv = finderPreviewData;
    if (!pv || !finderPick) return;
    const { cand, places } = finderPick;
    if ('role' in to) {
      const one = { ...cand, roles: [cand.roles[to.role]], capitals: cand.capitals.slice(to.role, to.role + 1) };
      flyToPoints(storyPoints(pv.world, pv.civ, one, []), 'finder');
    } else {
      const d = foundDetail(pv.world, pv.civ, cand, places).places[to.place];
      if (d) flyToPoints([[d.x, d.y]], 'finder', 4);
    }
  };
  /** 「用这个世界」:新建中的世界就是它(还没生成好就接着生成),回到新建第 2 步,种子和推演设定锁着 */
  const takeFinderPick = () => {
    const back = finderBack.current;
    const pick = finderPick;
    const run = getFinder().run;
    if (!back || !pick || !run) return;
    finderPreview(pick.row.seed);
    // 放宽了一点的:记下的说法、交界几国、撑多少年照放宽以后的门槛(就是判它合的那一套)
    const q = variantOf(run.query, getFinder().variant);
    const { cand, places } = pick;
    const pv = finderPreviewData;
    const fixed = run.setup.map === 'fixed';
    const fp = foundPickOf(q, cand, places, pv ? foundDetail(pv.world, pv.civ, cand, places) : null, { map: fixed ? 'fixed' : 'each', params: back.target.params });
    setFound({
      mapSeed: fixed ? back.target.params.seed : pick.row.seed,
      civSeed: pick.row.seed,
      year: cand.year,
      roles: fp.roles.map((r) => ({ role: r.role, name: r.name })),
      places: [...new Set(fp.places.map((p) => p.title))],
      pick: fp,
      pts: pv ? storyPoints(pv.world, pv.civ, cand, places) : [],
      gen: genSigOf(targetRef.current!.params, targetRef.current!.edits),
      ...(outlineSrc ? { from: outlineSrc.from, outline: outlineSrc.from.plots.length } : {}),
    });
    closeFinder();
    setCivHighlight(null);
    applyMapView(back.view);
  };
  /** 从大纲页来的:大纲搬到建好的这个世界,国家换成找到的那几国,对不上的标「要重新指」(outlineMove.ts);不是 = null */
  const moveFoundOutline = (f: NonNullable<typeof found>) => {
    const civNow = realCivRef.current;
    const t = targetRef.current;
    if (!f.from || !civNow || !t || civNow.seed !== f.civSeed) return null;
    const moved = moveOutline(f.from, f.pick.query, f.pick.roles.map((r) => r.polity), civNow, f.pick.map === 'fixed' && f.from.mapKey === mapKeyOf(t.params, getEdits()));
    if (moved.plots.length) setOutlinePlots(moved.plots);
    return moved;
  };
  /**
   * 照故事找的世界建好了:隘口、交界加成作者标记,侧栏顶上记一组「照故事找的」(foundStore.ts),提示一次;
   * 新建界面淡出以后地图飞到故事里的几国
   */
  const foundCreated = (f: NonNullable<typeof found>) => {
    const id = targetRef.current?.id;
    const w = data?.world;
    if (!id || !w) return;
    const spots = f.pick.places.map((p) => {
      const mark = addMark({ title: p.title, color: p.kind === 'pass' ? 'orange' : 'purple', from: f.year, at: [w.mesh.x[p.cell], w.mesh.y[p.cell]], note: `照故事找的：${p.note}` });
      return { ...p, mark };
    });
    putFound(id, { ...f.pick, places: spots });
    const moved = moveFoundOutline(f);
    setFound(null);
    if (isStored(id))
      showToast({
        id: 'created',
        kind: 'ok',
        dot: true,
        text: `建好了，停在第 ${f.year} 年`,
        more: [
          ...(f.places.length ? [`${f.places.join('、')}加成了地图上的标记，不要了在「标记」里删`] : []),
          ...(moved?.plots.length ? [`大纲带过来了${moved.redo ? `，${moved.redo} 条有对不上的，在「大纲」里标着「要重新指」` : ''}`] : []),
        ],
        ttl: 7000,
      });
    foundFly.current = { id, polities: f.pick.roles.map((r) => r.polity), year: f.year, pts: f.pts };
  };
  /** 侧栏「照故事找的」点「再找」:照搜的时候的世界参数新建一个世界,打开找世界那一页,条件照这次的(还没走的那批结果接着用) */
  const findAgainNow = (p: FoundPick) => {
    openTarget(draftTarget(p.params));
    if (!draftNow()) return;
    setQuery(p.query);
    setFinderMap(p.map);
    openFinderPage();
  };
  const findAgainRef = useRef(findAgainNow);
  findAgainRef.current = findAgainNow;
  useEffect(() => {
    setFindAgainHandler((p) => findAgainRef.current(p));
    return () => setFindAgainHandler(null);
  }, []);
  /**
   * 大纲页「找更合的世界」:照这个世界新建一个(世界参数、地形、推演年数、拓荒、起源、天灾、地名风格、纪年照原来的),打开找世界那一页;
   * 大纲里写到最多的几国先列成故事里的国家(叫法用大纲里的国名,条件空着让作者加)。建好以后大纲搬过去(foundCreated)
   */
  const findForOutlineNow = () => {
    const cur = currentWorld();
    const t = targetRef.current;
    const civNow = realCivRef.current;
    const e = getEdits();
    if (!cur || !t || t.kind === 'draft' || !civNow || !e.outline?.plots.length) return;
    const from = outlineFrom({ civ: civNow, plots: e.outline.plots, marks: e.marks, characters: e.characters }, cur.id, mapKeyOf(t.params, e));
    const view = { base: mapViewRef.current.base, fill: mapViewRef.current.fill };
    const { endYear, frontier, origins, calamity, nameMix, era, months, sketch } = e;
    const keep: WorldEdits = {
      ...EMPTY_EDITS,
      terrain: [...e.terrain],
      ...(sketch ? { sketch } : {}),
      ...(nameMix ? { nameMix } : {}),
      ...(endYear ? { endYear } : {}),
      ...(frontier ? { frontier } : {}),
      ...(origins ? { origins } : {}),
      ...(calamity ? { calamity } : {}),
      ...(era ? { era } : {}),
      ...(months !== undefined ? { months } : {}),
    };
    closeOverview();
    openTarget(draftTarget(t.params, null, keep));
    if (!draftNow()) return;
    setQuery({ roles: outlineRoles(from), together: [] });
    setFinderMap('each');
    setOutlineSrc({ from, view });
    openFinderPage();
  };
  const findOutlineRef = useRef(findForOutlineNow);
  findOutlineRef.current = findForOutlineNow;
  useEffect(() => {
    setOutlineFinder(() => findOutlineRef.current());
    return () => setOutlineFinder(null);
  }, []);
  /** 照故事找的世界建好、新建界面淡出以后:地图飞到故事里的几国 */
  const foundFly = useRef<{ id: string; polities: number[]; year: number; pts: [number, number][] } | null>(null);
  useEffect(() => {
    const ff = foundFly.current;
    if (!ff || studioOut !== 0 || draft || !data || !realCiv || currentWorld()?.id !== ff.id) return;
    foundFly.current = null;
    // 「用这个世界」时按那个世界算好的那一块;没算好(还在生成就点了)按几国那年的州
    let pts = ff.pts;
    if (!pts.length) {
      const own = ownersAt(realCiv, ff.year).polity;
      const seat = realCiv.regions.seat;
      pts = [];
      for (let r = 0; r < own.length; r++) if (ff.polities.includes(own[r])) pts.push([data.world.mesh.x[seat[r]], data.world.mesh.y[seat[r]]]);
    }
    flyToPoints(pts, 'world');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studioOut, draft, data, realCiv]);
  /** 「用这个世界」以后、新建中的世界还是找到的那个(换了种子、文明种子就不算了) */
  // (改了世界参数、地形、草图也不算:国家、地方对不上了)
  const foundNow =
    found && draft && !finderOn && found.gen === genSigOf(params, edits) && (cleanCivSeed(edits.civSeed) ?? params.seed) === found.civSeed ? found : null;
  // ---- 浏览器的后退、前进(nav.ts):换到记着的那一步 ----
  /** 离开时还没存着的世界(只是看看的、别人分享的):退回来时照原样打开(只记在这一页里,刷新就没了) */
  const navTargets = useRef(new Map<string, Target>());
  /** 要离开这个画面了:名字、存没存着;没存着的世界记下它 */
  const describeNav = () => {
    const t = targetRef.current;
    // 在我的世界:targetRef 还是上一个世界(可能已经删了),不算
    if (!t || getStage().stage === 'home') return {};
    const cw = currentWorld();
    const live = cw?.id === t.id;
    const title = (live ? cw.title : t.title) || undefined;
    const stored = isStored(t.id);
    // 没存着的、最近的修改没写进浏览器的(存储满了):记下现在的样子(修改、名字用手上的),回来时照这个打开;存好了的不用记。
    // 新建中的只记动过、没写进去的(还在生成就起了名的也算;没动过的按网址里的种子新建就是原样)
    const unsaved = live && currentUnsaved();
    const touched = live ? !cw.pristine : !t.pristine;
    if ((!stored && (t.kind !== 'draft' || touched)) || unsaved) navTargets.current.set(t.id, { ...t, ...(live ? { edits: getEdits(), title } : {}), ...(unsaved && t.kind === 'draft' ? { pristine: false } : {}), view: undefined, warnings: undefined });
    else navTargets.current.delete(t.id);
    return { title, stored };
  };
  /** 现在这个世界生成好、历史推完了(干预、地形大事都推进去了):它的编号;还没好 = null */
  const settledId = (): string | null => {
    const t = targetRef.current;
    const cw = currentWorld();
    if (getStage().stage !== 'world' || !t || !cw || cw.id !== t.id || !rawRef.current || fresh.current || regenRef.current) return null;
    if (!sameInterventions(getEdits().interventions, civEdits.current) || !sameUpheavals(getEdits().upheavals, civUps.current)) return null;
    const ri = resimInfo.current;
    return ri && ri.arrived === undefined ? null : t.id;
  };
  /**
   * 按后退 / 前进到了 to 这一步:
   *   我的世界  回我的世界
   *   新建      还是这次新建(同一个编号):种子、参数换回那一步的(那一步的网址里记着);存着、没建完的:打开它(同样换回;
   *             这一页里记着的、存储满了没写进去的,照这一页里的样子打开);
   *             已经建成了世界的:后退时跳过(前面没有这个网站的一步了就回我的世界),前进时打开那个世界;
   *             存过、没建完就删掉了的(以它为底稿新建、什么都没动就返回的那一份):后退时同样跳过;没存过的:按网址里的种子新建
   *             (照手绘图、还没照图长出星球的:图没留下,回我的世界、弹窗停在选图那一步)
   *   世界      这一页里看过、没存着的(或最近的修改没写进浏览器,存储满了):照这一页里的样子打开;存着的:打开它;
   *             存过、现在不在了:回我的世界,提示删掉了;
   *             别的(网址里带种子的、分享短链接):按网址打开
   * 从"以它为底稿新建"离开、什么都没动:那一份删掉(和左上的返回一样)
   */
  const routeNav = (to: NavState, from: NavState, dir: -1 | 1): void | 'skip' => {
    if (from.page === 'draft') {
      const left = derivedUntouched();
      if (left && !(to.page === 'draft' && to.id === left)) deleteWorld(left);
    }
    // 分享链接打不开的那一页、正在取的分享、「新建世界」弹窗、写史书的窗口(选的是那个世界的国家)、读着的史书:换了画面就不留
    // (到了世界、那一步记着史书的,世界好了再打开)
    setLanding(null);
    setNewDlg(null);
    clearToast('share');
    closeHistoryBook();
    closeBookReader();
    if (to.page === 'home') return showHome();
    // 作品墙那一页、一个作品(取的时候换了画面,取回来不再打开)
    if (to.page === 'gallery') return to.id ? openWork(to.id) : showGallery();
    wallSeq.current++;
    setWall(null);
    // 回到从作品墙打开的世界作品:左上那一条照旧
    const wi = to.page === 'world' && to.id ? workItems.current.get(to.id) : undefined;
    setWorkFor(wi && to.id ? { id: to.id, work: wi } : null);
    const back = dir < 0;
    const skip = (): void | 'skip' => (back && to.prev ? 'skip' : showHome());
    const url = readUrl();
    const q = new URLSearchParams(location.search);
    if (to.page === 'draft') {
      const seed = to.seed ?? url.params.seed;
      const want = { ...url.params, seed };
      const d = draftNow();
      if (d && d.id === to.id) {
        if (worldKey(want) !== worldKey(d.params) && !d.base) draftSeed(seed, want);
        return;
      }
      const w = to.id ? loadWorld(to.id) : null;
      if (w && !w.draft) return back ? skip() : openStored(w.id);
      const once = to.stored || (!!to.id && q.get('w') === to.id);
      const mem = to.id ? navTargets.current.get(to.id) : undefined;
      // 这一页里记着的(最近的修改没写进浏览器,存储满了)比存着的新;同样换回那一步的种子、参数
      if (mem?.kind === 'draft' && (w || !once)) {
        openTarget(mem);
        if (worldKey(want) !== worldKey(mem.params) && !mem.base) draftSeed(seed, want);
        return;
      }
      if (w) {
        openStored(w.id);
        if (worldKey(want) !== worldKey(w.save.params) && !w.base) draftSeed(seed, want);
        return;
      }
      // 存过(离开时记着,或那一步的网址里有 w=编号)、现在不在了:跳过
      if (once) return skip();
      // 照手绘图新建、还没照图长出星球(图不存,离开就没了):和刷新时一样,回我的世界,弹窗停在照手绘图选图那一步
      if (q.get('new') === 'image') {
        showHome();
        setNewDlg({ init: { mode: 'image', params: url.params, step: 2, endYear: url.years } });
        return;
      }
      return openTarget({ ...draftTarget({ ...url.params, seed }, null, yearsEdits(url.years)), id: to.id ?? newWorldId() });
    }
    const w = to.id ? loadWorld(to.id) : null;
    const once = to.stored || isWorldId(q.get('w'));
    const mem = to.id ? navTargets.current.get(to.id) : undefined;
    // 这一页里记着的(没存着的、最近的修改没写进浏览器的)比存着的新;存过、现在不在了的是删掉了
    if (mem && (w || !once)) return openTarget(mem);
    if (w) return openStored(w.id);
    if (once) {
      showHome();
      goneToast(to.title);
      return;
    }
    const code = q.get('s');
    if (code) {
      // 刷新过(手上没有这个世界):和打开分享短链接时一样,先到"正在打开"那一页,停了、打不开也显示在那一页
      pausePlayback();
      setReplayOn(false);
      enterStage('home');
      setLanding('loading');
      return openShortShare(code, () => sameScreen(getNav(), to));
    }
    // 从作品墙打开、还没存下的世界作品(刷新过,手上没有这个世界):和打开作品的网址一样再取一次
    const gid = q.get('gallery');
    if (gid) return openWork(gid);
    if (q.has('seed')) return openTarget({ ...visitTarget(url.params, url.gen), id: to.id ?? newWorldId() });
    return showHome();
  };
  const navRef = useRef<NavHooks>(null as unknown as NavHooks);
  navRef.current = { route: routeNav, describe: describeNav, settled: settledId, apply: (l) => (shownRaw ? applyNavLayer(shownRaw, l) : {}) };
  // 只是看看的世界改了第一笔、新建中的动了第一下,就存下了:网址换成 w=编号,刷新还回到它
  useEffect(() => {
    const t = targetRef.current;
    const cur = currentWorld();
    if (home || !t || !cur || cur.id !== t.id) return;
    if (isStored(t.id) && new URLSearchParams(location.search).get('w') !== t.id) writeWorldUrl(t);
  }, [v, home]);
  // 把 .json 拖进页面 = 从文件打开;照手绘图新建时拖进来的图片 = 换成这张重新认(随机生成的新建不收图片,松手时说一句)
  const [dropping, setDropping] = useState<false | 'save' | 'image'>(false);
  const hasFiles = (e: React.DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes('Files');
  /** 新建中拖进来图片:照手绘图的收下,随机生成的不收 */
  const imageDrop = (): 'image' | false | null => (getStage().stage !== 'draft' ? null : draftModeOf(targetRef.current) === 'image' ? 'image' : false);
  const onDragOver = (e: React.DragEvent) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    const img = imageDrop();
    const kind = img !== null && e.dataTransfer.items?.[0]?.type.startsWith('image/') ? img : 'save';
    if (dropping !== kind) setDropping(kind);
  };
  const onDragLeave = (e: React.DragEvent) => {
    if (!e.relatedTarget || !(e.currentTarget as Node).contains(e.relatedTarget as Node)) setDropping(false);
  };
  const onDrop = (e: React.DragEvent) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    setDropping(false);
    const f = e.dataTransfer.files[0];
    if (!f) return;
    const img = imageDrop();
    if (img !== null && isImageFile(f)) {
      if (img) return void startImport(f);
      return void notify({ kind: 'warn', text: '随机生成的世界不能导入图片，想照图生成就新建一个' });
    }
    f.text().then(
      (t) => openText(t, f.name),
      () => notify({ kind: 'error', text: `打不开 ${f.name}`, more: ['读不了这个文件'] }),
    );
  };

  // ---- 渲染 ----
  // 画好的整张图按「画风 / 图层」各存一份(离屏画布),同一个世界里切回去直接贴上;
  // 地形大事前后是两张图,各存一份(最近的 MAP_KEEP 张;来回拖时间轴不用重画),世界一换就清空。
  // 用画布对画布复制而不是 getImageData,不从显卡读回像素,
  // 免得浏览器把主画布降级成软件渲染(那样河流、墨线的抗锯齿会变样)。
  // 用 useLayoutEffect:地形先于文明层(CivLayer 里的 useEffect)画好 —— 手绘风的文明层要借地形的符号层给水彩"让位"。
  const cacheRef = useRef<{ data: { raster: Raster }; base: unknown; maps: Map<string, HTMLCanvasElement> }[]>([]);
  /**
   * d 这一张图的缓存(用到的挪到最前);同一个世界(同一张生成出来的主图、地块索引是同一份)留最近 MAP_KEEP 张,别的释放。
   * 编辑地形涂一笔以后主图换了一张(地块索引还是那一份):旧主图的几张也放掉,不再当成同一个世界的另一段留着
   */
  const mapsOf = (d: { raster: Raster }): Map<string, HTMLCanvasElement> => {
    const list = cacheRef.current;
    const hit = list.find((e) => e.data === d);
    if (hit) {
      cacheRef.current = [hit, ...list.filter((e) => e !== hit)];
      return hit.maps;
    }
    const base = baseRef.current?.raster;
    const keep = list.filter((e) => e.base === base && e.data.raster.cell === d.raster.cell).slice(0, MAP_KEEP - 1);
    for (const e of list) if (!keep.includes(e)) for (const c of e.maps.values()) c.width = c.height = 0; // 尽快释放显存
    const maps = new Map<string, HTMLCanvasElement>();
    cacheRef.current = [{ data: d, base, maps }, ...keep];
    return maps;
  };
  eraCached.current = (d, key) => !!cacheRef.current.find((e) => e.data === d)?.maps.has(key);
  /** 弯边投影:地形图(缓存里的等距圆柱原图)按投影铺到屏幕上 */
  const terrainProj = useRef(new ProjLayer());
  /** 上次画的是哪个世界、哪种画风 / 图层(弯边投影下只改中心时只重铺,不算"画了新的一张") */
  const drawnKey = useRef<{ data: unknown; key: string } | null>(null);
  /** 地图视图:缩放倍数、平移(见下面"缩放 / 平移") */
  const [view, setView] = useState({ k: 1, x: 0, y: 0 });
  /**
   * 弯边投影、放大到细节层盖住整个视口(TerrainDetail 按投影重画了看得见的那一块):底下这张整图看不见,
   * 不用按投影精画(整图精画一次几百毫秒),整图重铺就够了(露边时也对得上);缩小到细节层以下再精画
   */
  const terrainCovered = curved && view.k > DETAIL_K && (style === 'fantasy' || style === 'realistic');
  /** 按新地形重新生成的世界画到地形图上了:记下下一帧(地图在屏幕上换上)的时刻(冒烟检查、测速用) */
  const noteShown = () => {
    const rg = regenRef.current;
    if (!rg || rg.arrived === undefined || rg.shown !== undefined) return;
    rg.shown = -1;
    requestAnimationFrame(() => (rg.shown = performance.now() - rg.t0));
  };
  useLayoutEffect(() => {
    const cv = canvasRef.current;
    if (!cv || !data) return;
    const { world, raster } = data;
    const maps = mapsOf(data);
    const key = baseKeyOf(style, layer, paintedLook);
    const render = (ctx: CanvasRenderingContext2D) => {
      if (style === 'realistic') renderRealistic(ctx, world, raster, paintedLook);
      else if (style === 'fantasy') renderFantasy(ctx, world, raster);
      else renderLayer(ctx, world, raster, layer);
    };
    const t0 = performance.now();
    const hit = maps.get(key);
    const fresh = drawnKey.current?.data !== data || drawnKey.current.key !== key;
    drawnKey.current = { data, key };
    if (mp) {
      // 弯边投影:原图画在离屏画布上(和等距圆柱共用缓存),按投影铺到屏幕上;不接右边那一份
      let src = hit;
      if (!src) {
        src = document.createElement('canvas');
        src.width = raster.w;
        src.height = raster.h;
        render(src.getContext('2d')!);
        maps.set(key, src);
      }
      const t1 = performance.now();
      const proj = terrainProj.current;
      // 编辑地形后在后台按投影画好的那一版(同一张图、同一个投影和中心、同一种画风和画法)
      const p = preProj.current;
      const pre = p && p.raster === raster && p.key === mp.key && p.style === style && (style !== 'realistic' || p.look === paintedLook) ? p.canvas : null;
      preProj.current = null;
      presentTerrain(cv, mp, { world, raster, style, look: terrainLook, src, layer: proj, moving: projMoving || terrainCovered, pre, swap: !fresh });
      if (p) p.canvas.width = p.canvas.height = 0;
      mirrorCanvas(canvasCopyRef.current, null, false);
      const w = window as unknown as { __wf: unknown; __wfProj: unknown };
      w.__wfProj = { proj: mp.def.id, lon: mp.lon0, ms: performance.now() - t1, pending: terrainRefining() };
      if (fresh) w.__wf = { ready: !mapFirst.current?.shown, renderMs: performance.now() - t0, style, layer, proj: mp.def.id };
      noteShown();
      dropPreparedRivers(raster.water);
      return;
    }
    terrainProj.current.release();
    cv.width = raster.w;
    cv.height = raster.h;
    const ctx = cv.getContext('2d')!;
    if (hit) ctx.drawImage(hit, 0, 0);
    else render(ctx);
    const renderMs = performance.now() - t0;
    if (!hit) {
      const copy = document.createElement('canvas');
      copy.width = raster.w;
      copy.height = raster.h;
      copy.getContext('2d')!.drawImage(cv, 0, 0);
      maps.set(key, copy);
    }
    // 右边再接一份(左右无限拖动)
    mirrorCanvas(canvasCopyRef.current, cv, true);
    // 检查脚本用:画好了(mark 没了);ready = 世界齐了(地图先换上的新建世界,历史到了才算,见 takeCiv)
    (window as unknown as { __wf: unknown }).__wf = { ready: !mapFirst.current?.shown, renderMs, style, layer };
    noteShown();
    // 给这张图后台描好的河没用上(换上前换了画风、缓存里本来就有):放掉
    dropPreparedRivers(raster.water);
  }, [data, style, layer, paintedLook, terrainLook, mp, projMoving, terrainCovered]);

  /**
   * 某画风的整张底图(等距圆柱,和 raster 一样大):缓存里有就直接给,没有就画一张放进缓存(图层缩略图用;之后切过去也不用再画)。
   * 默认画地图上这一段的;d = 别的段的世界和主图(存档缩略图画结束那一年的)
   */
  const baseCanvas = useCallback((key: string, d0?: { world: World; raster: Raster }): HTMLCanvasElement | null => {
    const d = d0 ?? dataRef.current;
    if (!d) return null;
    const maps = mapsOf(d);
    let c = maps.get(key);
    if (!c) {
      c = document.createElement('canvas');
      c.width = d.raster.w;
      c.height = d.raster.h;
      const ctx = c.getContext('2d');
      if (!ctx) return null;
      if (key === 'realistic') renderRealistic(ctx, d.world, d.raster);
      else if (key.startsWith('realistic:')) renderRealistic(ctx, d.world, d.raster, key.slice(10) as SurfaceLook);
      else if (key === 'fantasy') renderFantasy(ctx, d.world, d.raster);
      else renderLayer(ctx, d.world, d.raster, key.slice(5) as LayerId);
      maps.set(key, c);
    }
    return c;
  }, []);
  // 缩略图和地图画同一段:时间轴在地形大事以前时,底图是那一段的,州也要用那一段的(shownRaw)
  // 编辑地形换上的新地形:缩略图先留着涂之前的,停笔一会儿再重画;正在按新地形重新生成时先不画
  const { thumbs, request: requestThumbs } = useLayerThumbs(
    { data, civ: shownRaw, baseCanvas, edited: editedRef.current, busy: !!progress?.regen },
    baseThumb(mapBase, satLook),
  );
  /** 正在画的底图(缩略图上转圈;画好之前地图先留着原来的) */
  const [pendingBase, setPendingBase] = useState<{ base: BaseId; sat: SatLook } | null>(null);
  const pickTok = useRef(0);
  /**
   * 点了一种底图(或卫星画法):缓存里有就直接换;没有就先在缩略图上转圈、让界面画一帧,画好整张再换过去;
   * 没画出来就留在原来的底图,顶上提示带「重试」
   */
  const pickBase = useCallback(
    (base: BaseId, sat: SatLook = mapViewRef.current.sat) => {
      const d = dataRef.current;
      const b = baseLook(base, sat);
      const key = baseKeyOf(b.style, b.data ?? layer, paintLook(b.look ?? surface, mapViewRef.current.fill));
      clearToast('base-fail');
      if (!d || mapsOf(d).has(key)) {
        pickTok.current++;
        setPendingBase(null);
        return applyMapView({ base, sat });
      }
      const tok = ++pickTok.current;
      const was = mapViewRef.current;
      setPendingBase({ base, sat });
      requestAnimationFrame(() =>
        requestAnimationFrame(() => {
          if (tok !== pickTok.current) return;
          let ok = false;
          try {
            ok = !!baseCanvas(key, d);
          } catch (e) {
            console.error('底图没画出来', e);
          }
          setPendingBase(null);
          if (dataRef.current !== d) return;
          if (ok) return applyMapView({ base, sat });
          showToast({
            id: 'base-fail',
            kind: 'error',
            text: `${baseName(base, sat)}没画出来，地图还是${baseName(was.base, was.sat)}`,
            more: ['年份、位置、选中的都没动'],
            action: { label: '重试', act: 'base-retry', onClick: () => pickBase(base, sat) },
          });
        }),
      );
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [applyMapView, baseCanvas, layer, surface],
  );

  // ---- 回放:看世界长出来 ----
  const startReplay = () => {
    if (!data || !genParams.current) return;
    setTerrainTool({ on: false });
    closeUpheaval();
    prepareCivReplay(); // 文明层先退回第 0 年,等地质放完再接着放文明
    setReplayOn(true);
    if (replay) setReplay({ ...replay, idx: 0 });
    else send({ type: 'history', id: reqId.current, params: genParams.current, terrain: [...genTerrain.current], sketch: genSketch.current });
  };
  /** 弯边投影:回放帧先放在离屏的等距圆柱原图上,再按投影铺到屏幕上 */
  const overlayProj = useRef(new ProjLayer());
  useEffect(() => {
    if (!replayOn || !replay) return;
    const cv = overlayRef.current;
    if (!cv) return;
    const frame = new ImageData(new Uint8ClampedArray(replay.frames[replay.idx]), replay.w, replay.h);
    const m = mpRef.current;
    if (m) {
      overlayProj.current.source(replay.w, replay.h).getContext('2d')!.putImageData(frame, 0, 0);
      overlayProj.current.present(cv, m, pageColor(style));
      mirrorCanvas(overlayCopyRef.current, null, false);
    } else {
      cv.width = replay.w;
      cv.height = replay.h;
      cv.getContext('2d')!.putImageData(frame, 0, 0);
      mirrorCanvas(overlayCopyRef.current, cv, !!data);
    }
    const last = replay.idx >= replay.frames.length - 1;
    const t = setTimeout(
      () => (last ? (setReplayOn(false), getStage().stage === 'world' && startCivReplay()) : setReplay((r) => (r ? { ...r, idx: r.idx + 1 } : r))),
      last ? 1400 : replay.idx === 0 ? 900 : 260,
    );
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [replayOn, replay]);
  // 回放时改了投影 / 中心:这一帧按新的重铺(不打断回放的节奏)
  useEffect(() => {
    const cv = overlayRef.current;
    if (!cv || !replayOn || !replay) return;
    if (mp && overlayProj.current.has()) overlayProj.current.present(cv, mp, pageColor(style));
    else if (!mp) overlayProj.current.release();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mp]);

  // ---- 地图铺满全屏:2:1 的地图框按舞台"盖满"(舞台比 2:1 窄时上下正好顶到边、左右接着转;比 2:1 宽时左右顶到边) ----
  const [box, setBox] = useState({ w: 0, h: 0 });
  /** 舞台(视口)的大小:视窗、平移范围按它算 */
  const [stageSize, setStageSize] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => {
      const W = e.contentRect.width;
      const H = e.contentRect.height;
      const w = Math.max(100, W, H * 2);
      setBox({ w, h: w / 2 });
      setStageSize({ w: e.contentRect.width, h: e.contentRect.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // ---- 缩放 / 平移(视图 view 在上面"地形图"那里声明)----
  /** 按下时的位置、视图(弯边投影:还有当时的中央经线;拖动改的是它) */
  const drag = useRef<{ x: number; y: number; vx: number; vy: number; lon: number; touch?: boolean } | null>(null);
  // 世界东西相连:左右无限拖动(见 mapWrap.ts)。wrapW = 一整圈的世界宽度,还没有世界时 0
  const wrapW = data ? wrapOf(data.world) : 0;
  setTerrainWrap(wrapW);
  // 编辑地形的高度笔按地图上现在这个世界读海拔
  setTerrainProbe(data);
  /**
   * 窄屏底部被卡片和时间轴胶囊盖住的那一截:没选东西时是收起的世界卡片 + 胶囊,详情卡片开着时是半高的卡片 + 胶囊。
   * 地图可以往上推进这一截(见 mapWrap.ts 的 StageBox.padB),下半截的国家也能飞到上方看得见的地方;卡片收回去后慢慢回到原来的范围
   */
  const padB = !narrow || !stageSize.h ? 0 : Math.max(0, stageSize.h - phoneFree(stageSize.h, panelOpen)[1]);
  const geo = useRef<{ wrap: number; bw: number; bh: number; W: number; H: number; padB: number }>({ wrap: 0, bw: 0, bh: 0, W: 1, H: 1, padB: 0 });
  geo.current = { wrap: wrapW, bw: box.w, bh: box.h, W: data?.world.width ?? 1, H: data?.world.height ?? 1, padB };
  const curvedRef = useRef(curved);
  curvedRef.current = curved;
  /**
   * 平移范围:上下夹在两极以内;等距圆柱左右不限(挪整数圈),
   * 弯边投影横向正对外框(左右拖动改中央经线,见 mapWrap.ts 的 clampCurved)
   */
  const clampAny = (v: { k: number; x: number; y: number }, w: number, h: number) => {
    const g = geo.current;
    if (!g.bw) return v;
    const b = { sw: w, sh: h, bw: g.bw, bh: g.bh, padB: g.padB };
    return curvedRef.current ? clampCurved(v, b) : clampSphere(v, b);
  };
  const clampRef = useRef(clampAny);
  clampRef.current = clampAny;
  const sb: StageBox = { sw: stageSize.w, sh: stageSize.h, bw: box.w, bh: box.h, padB };
  /** 视窗中心的世界 x(舞台、地图框大小变了按它保持中心不动) */
  const centerRef = useRef<number | null>(null);
  /** 网址里带的中央经线:世界、舞台都出来以后把等距圆柱的视图转过去(只一次) */
  const pendingLon = useRef<number | null>(init.lon);
  // 换投影:缩放复位,中心不变(等距圆柱把视图转到这条经线;弯边投影横向正对外框)。
  // 在渲染时就换好视图,不会有一帧"新投影 + 旧视图"把中心记错
  const [viewProj, setViewProj] = useState<MapProjection>(projection);
  /** 从地球仪切出来时它正对着的经度:这一次提交后记进中心(渲染时只读、不改 store) */
  const handoffLon = useRef<number | null>(null);
  if (viewProj !== projection) {
    const fromGlobe = viewProj === 'globe' ? globeApi.current?.centerLon() : undefined;
    const lonNow = fromGlobe !== undefined ? wrapLon(fromGlobe) : getMapCenter();
    if (fromGlobe !== undefined) handoffLon.current = lonNow;
    setViewProj(projection);
    const base = { k: 1, x: 0, y: 0 };
    if (sb.sw && sb.bw) setView(curved || !wrapW ? clampCurved(base, sb) : viewCentredAt(base, sb, wrapW, xOfLon(lonNow, wrapW)));
    else setView(base);
  }
  useLayoutEffect(() => {
    if (handoffLon.current === null) return;
    publishMapCenter(handoffLon.current);
    handoffLon.current = null;
  });
  /** 这一次提交里视图刚被换掉(还是旧的):先不按它记中心,等下一次 */
  const settling = useRef(false);
  // 世界出来了、或者舞台大小变了,重新夹一下(保持中心经线不动)
  useEffect(() => {
    if (!sb.sw || !sb.bw || !wrapW) return;
    if (curvedRef.current) {
      pendingLon.current = null;
      setView((v) => clampCurved(v, sb));
      return;
    }
    let c = centerRef.current;
    if (pendingLon.current !== null) {
      c = xOfLon(pendingLon.current, wrapW);
      pendingLon.current = null;
      settling.current = true;
    }
    setView((v) => (c === null ? clampSphere(v, sb) : viewCentredAt(v, sb, wrapW, c)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wrapW, sb.sw, sb.sh, sb.bw, sb.bh]);
  // 窄屏详情卡片关上(地图不能再往上推进卡片那一截了):推上去的地图约 0.3 秒回到范围里
  const lastPadB = useRef(padB);
  useEffect(() => {
    const was = lastPadB.current;
    lastPadB.current = padB;
    if (padB >= was || !sb.sw || !sb.bw || flyRaf.current) return;
    const v0 = viewRef.current;
    const clamp = (v: { k: number; x: number; y: number }) => (curvedRef.current ? clampCurved(v, sb) : clampSphere(v, sb));
    const y1 = clamp(v0).y;
    if (Math.abs(y1 - v0.y) < 0.5) return;
    const t0 = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const t = animProgress(now, t0, 300);
      // 用户按下地图 / 又飞走了:让给它们
      if (flyRaf.current || drag.current) return;
      const v = { k: v0.k, x: v0.x, y: v0.y + (y1 - v0.y) * easeOutCubic(t) };
      viewRef.current = v;
      setView(t < 1 ? v : clamp(v));
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [padB]);
  // 当前中心经度:等距圆柱时视图一变就记下(之后的"中央经线"设置、导出读它);
  // 弯边投影和地球仪时中心就在 store 里,由它们自己改,不从平面视图推
  useEffect(() => {
    const ready = !!wrapW && !!sb.sw && !!sb.bw;
    if (projection !== 'equirect') {
      const lon = getMapCenter();
      centerRef.current = ready ? xOfLon(lon, wrapW) : null;
      (window as unknown as { __wfView: unknown }).__wfView = { ...view, wrap: wrapW, lon, bw: sb.bw, sw: sb.sw, proj: projection };
      return;
    }
    // 网址里带的中心还没转过去(世界还没出来),或者视图刚被换掉:先别把旧视图的中心记下
    if (pendingLon.current !== null) return;
    if (settling.current) {
      settling.current = false;
      return;
    }
    const cx = ready ? centerX(view, sb, wrapW) : null;
    centerRef.current = cx;
    const lon = cx === null ? getMapCenter() : lonOfX(cx, wrapW);
    publishMapCenter(lon);
    (window as unknown as { __wfView: unknown }).__wfView = { ...view, wrap: wrapW, lon, bw: sb.bw, sw: sb.sw, proj: projection };
  });
  useEffect(() => {
    handleMapCenterRequests((lon) => {
      stopFly(); // "设为中心"等:正在飞的停下,别再盖掉它
      if (getGlobeOn()) return globeApi.current?.flyTo(lon);
      const g = geo.current;
      const el = stageRef.current;
      // 弯边投影:中心就是中央经线,直接改(整图按它重投影)
      if (getProjection() !== 'equirect') {
        publishMapCenter(wrapLon(lon));
        return;
      }
      if (!g.wrap || !el || !g.bw) {
        publishMapCenter(wrapLon(lon));
        pendingLon.current = wrapLon(lon);
        return;
      }
      const b = { sw: el.clientWidth, sh: el.clientHeight, bw: g.bw, bh: g.bh };
      setView((v) => viewCentredAt(v, b, g.wrap, xOfLon(lon, g.wrap)));
    });
    // 截图脚本、冒烟检查用:转到某经度;世界坐标 ↔ 屏幕坐标(取视窗里的那一份;弯边投影按投影)
    const w = window as unknown as Record<string, unknown>;
    w.__wfSetCenter = (lon: number) => requestMapCenter(lon);
    // 冒烟检查用:把视图放回某个样子(点选会让地图飞走;要在同一个视图下接着点时先放回来)
    w.__wfSetView = (v: { k: number; x: number; y: number }) => {
      stopFly();
      viewRef.current = v;
      setView(v);
    };
    w.__wfSetProjection = (p: MapProjection) => setProjection(p);
    // 编辑地形的检查脚本用:地图上现在这张(世界、主图)和投影,拿去从头整张重画、和画面逐像素比
    w.__wfMapData = () => ({ data: dataRef.current, mp: mpRef.current, style: drawView.current.style, look: drawView.current.look });
    w.__wfWorldToClient = worldToClient.current = (wx: number, wy: number): [number, number] | null => {
      const el = stageRef.current;
      const g = geo.current;
      if (!el || !g.bw) return null;
      const r = el.getBoundingClientRect();
      const b = { sw: r.width, sh: r.height, bw: g.bw, bh: g.bh };
      const v = viewRef.current;
      const m = mpRef.current;
      let x = wx;
      let y = wy;
      if (m) [x, y] = projectWorld(m, wx, wy);
      else if (g.wrap) x = nearX(wx, stageToWorld(r.width / 2, 0, v, b, g.W, g.H)[0], g.wrap);
      const [X, Y] = worldToStage(x, y, v, b, g.W, g.H);
      return [r.left + X, r.top + Y];
    };
    // 某一点的完整读数(群落、海拔、国家、最近城市……;悬停卡片只露一两行,冒烟检查读这个)
    w.__wfProbe = (cx: number, cy: number): string[] | null => probeRef.current(cx, cy);
    w.__wfClientToWorld = (cx: number, cy: number): [number, number] | null => {
      const el = stageRef.current;
      const g = geo.current;
      if (!el || !g.bw) return null;
      const r = el.getBoundingClientRect();
      const b = { sw: r.width, sh: r.height, bw: g.bw, bh: g.bh };
      const [x, y] = stageToWorld(cx - r.left, cy - r.top, viewRef.current, b, g.W, g.H);
      const m = mpRef.current;
      if (m) return unprojectWorld(m, x, y);
      return [x - g.W * Math.floor(x / g.W), y];
    };
    // 导出回放视频(框里一块):屏幕上的框 → 地图平面上的范围
    setFilmViewport(() => {
      const el = stageRef.current;
      const g = geo.current;
      if (!el || !g.bw) return null;
      const r = el.getBoundingClientRect();
      const b = { sw: r.width, sh: r.height, bw: g.bw, bh: g.bh };
      const v = viewRef.current;
      const m = mpRef.current;
      return {
        k: v.k,
        mapCss: g.bw,
        mp: m,
        worldW: g.W,
        plane: (cx: number, cy: number) => stageToWorld(cx - r.left, cy - r.top, v, b, g.W, g.H),
        key: `${v.k.toFixed(4)},${Math.round(v.x)},${Math.round(v.y)},${m?.key ?? ''},${g.bw},${r.width}x${r.height}`,
      };
    });
    return () => {
      handleMapCenterRequests(null);
      setFilmViewport(null);
    };
  }, []);
  // 弯边投影里拖动改中心:一帧最多改一次(每次改都要整图重铺)
  const centerFrame = useRef<{ raf: number; lon: number | null }>({ raf: 0, lon: null });
  const scheduleCenter = (lon: number) => {
    const c = centerFrame.current;
    c.lon = lon;
    if (c.raf) return;
    c.raf = requestAnimationFrame(() => {
      c.raf = 0;
      if (c.lon !== null) publishMapCenter(wrapLon(c.lon));
      c.lon = null;
    });
  };
  useEffect(() => () => cancelAnimationFrame(centerFrame.current.raf), []);
  /** 选中后地图正在飞过去(见下面"选中 → 暂停 + 地图飞过去");用户自己拖动、缩放就停下 */
  const flyRaf = useRef(0);
  const stopFly = () => {
    if (!flyRaf.current) return;
    cancelAnimationFrame(flyRaf.current);
    flyRaf.current = 0;
    if (curvedRef.current) setMapMoving(false);
  };
  /**
   * 以舞台上的 (mx, my) 为中心缩放 f 倍(滚轮、右下角的 + −)。
   * 弯边投影:上下照常以这一点为中心缩放;横向转中央经线,让这一点下的地方还在这一点下
   */
  const zoomAt = (mx: number, my: number, f: number) => {
    stopFly();
    directorHandBack();
    const el = stageRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const m = mpRef.current;
    const g = geo.current;
    if (m && g.bw) {
      // 缩放中心也在转:和拖动一样算"正在动"(整图先按投影重铺、细节层跟着挪),停一小会儿再按投影精画一次
      setMapMoving(true);
      clearTimeout(panIdle.current);
      panIdle.current = window.setTimeout(() => !drag.current && !pinch.current && setMapMoving(false), 150);
      const v = viewRef.current;
      const k = Math.min(12, Math.max(1, v.k * f));
      const b = { sw: rect.width, sh: rect.height, bw: g.bw, bh: g.bh, padB: g.padB };
      const nv = clampCurved({ k, x: v.x, y: my - (my - v.y) * (k / v.k) }, b);
      const [px, py] = stageToWorld(mx, my, v, b, g.W, g.H);
      const r = unprojectRel(m, px, py);
      if (r) {
        const kx = m.def.kx(r[1]);
        const [px2] = stageToWorld(mx, my, nv, b, g.W, g.H);
        if (kx > 1e-6) {
          const rel2 = Math.max(-Math.PI, Math.min(Math.PI, (px2 - g.W / 2) / (m.s * kx)));
          publishMapCenter(wrapLon(m.lon0 + ((r[0] - rel2) * 180) / Math.PI));
        }
      }
      viewRef.current = nv;
      setView(nv);
      return;
    }
    setView((v) => {
      const k = Math.min(12, Math.max(1, v.k * f));
      const q = k / v.k;
      const nx = mx - (mx - v.x) * q;
      const ny = my - (my - v.y) * q;
      return clampRef.current({ k, x: nx, y: ny }, rect.width, rect.height);
    });
  };
  const zoomRef = useRef(zoomAt);
  zoomRef.current = zoomAt;
  /**
   * 触控板两指滑动:平移(dx / dy = 滚轮的读数,地图往 −dx、−dy 挪,方向和滑动网页一样)。
   * 弯边投影:左右 = 转中央经线(和拖动一样),上下 = 平移;滑完停一小会儿算停下(国名按投影后的国土重新摆)
   */
  const panIdle = useRef(0);
  useEffect(() => () => clearTimeout(panIdle.current), []);
  const wheelPan = (dx: number, dy: number) => {
    stopFly();
    directorHandBack();
    const el = stageRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (hover) setHover(null);
    if (mp && box.w) {
      setMapMoving(true);
      clearTimeout(panIdle.current);
      panIdle.current = window.setTimeout(() => !drag.current && setMapMoving(false), 150);
      const pxPerDeg = view.k * (box.w / mp.W) * mp.s * mp.def.kx(0) * (Math.PI / 180);
      if (pxPerDeg > 0 && dx) scheduleCenter((centerFrame.current.lon ?? getMapCenter()) + dx / pxPerDeg);
      if (dy) setView((v) => clampRef.current({ k: v.k, x: v.x, y: v.y - dy }, rect.width, rect.height));
      return;
    }
    setView((v) => clampRef.current({ k: v.k, x: v.x - dx, y: v.y - dy }, rect.width, rect.height));
  };
  const panRef = useRef(wheelPan);
  panRef.current = wheelPan;
  // 滚轮:鼠标滚轮 / 捏合 = 缩放,触控板两指滑动 = 平移(怎么分见 wheel.ts)
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const read = createWheelReader();
    const onWheel = (e: WheelEvent) => {
      touchRef.current();
      // 详情面板里滚动 = 滚面板,不缩放地图;地球仪自己管缩放
      if ((e.target as HTMLElement | null)?.closest?.('.inspector') || getGlobeOn()) return;
      e.preventDefault();
      // Safari 的捏合已经按 gesture 事件缩放了(见下面"浏览器自己的页面缩放")
      if (e.ctrlKey && inGesturePinch()) return;
      const a = read(wheelSample(e));
      if (!a) return;
      const rect = el.getBoundingClientRect();
      if (a.kind === 'zoom') zoomRef.current(e.clientX - rect.left, e.clientY - rect.top, a.f);
      else panRef.current(a.dx, a.dy);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);
  /** 右下角的 + −:以看得见的地图中间为中心(宽屏让出左边的侧栏卡片);地球仪里交给地球仪自己缩放 */
  const zoomButton = (f: number) => {
    touchRef.current();
    const el = stageRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const cx = (sideRoom(rect.width) + rect.width - astRoom(rect.width)) / 2;
    const cy = rect.height / 2;
    directorHandBack();
    if (getGlobeOn()) return globeApi.current?.zoomBy(f, rect.left + cx, rect.top + cy);
    zoomAt(cx, cy, f);
  };

  // ---- 编年史点一条:事发地不在视野里,就把地图平移过去(不改缩放,约 0.4 秒滑过去) ----
  const chron = useChronicle();
  // 世界里开着的(选中、概览、史书)变了:画好以后报给 nav.ts(多打开一张算一步);世界好了再打开退回来的那一步记着的
  const ovNow = useOverview();
  const readerNow = useBookReader();
  useEffect(() => {
    if (stage !== 'world' || !shownRaw) return;
    const l = layerNow(shownRaw);
    if (l) navLayer(l);
  }, [stage, shownRaw, selState.sel, ovNow.open, ovNow.tab, chron.polity, readerNow.open, readerNow.key]);
  useEffect(() => {
    navSettled(navRef.current.settled());
  }, [stage, rawCiv, resim, edits, shownRaw]);
  const hl = useCivHighlight();
  const picking = usePolityPick();
  const viewRef = useRef(view);
  // 只在视图状态真的变了时跟上:滚轮缩放先改 viewRef 再 setView,改中心(store)触发的那次重画可能还没带上这次 setView,
  // 拿旧的视图盖回去的话,下一下滚轮就从旧的倍数算起(丢一下)
  const seenView = useRef(view);
  if (seenView.current !== view) {
    seenView.current = view;
    viewRef.current = view;
  }
  // 新建界面摊平改地形:舞台挪到中间那块(正好 2:1,地图框正好铺满),视图放回 1 倍、转到刚摊平时正中的经线
  // (等舞台换成那块的大小再转;同一次摊平只转一次)
  const flatSeq = useRef(0);
  useEffect(() => {
    const f = studioFlat;
    if (!studioOn || !f || f.lon === undefined || f.seq === flatSeq.current || !wrapW || !sb.bw) return;
    if (Math.abs(sb.sw - f.rect.w) > 1 || Math.abs(sb.sh - f.rect.h) > 1) return;
    flatSeq.current = f.seq;
    stopFly();
    // 整像素:主图和右边接的那一份正好对齐,接缝处不透出一道暗线
    const v0 = viewCentredAt({ k: 1, x: 0, y: 0 }, sb, wrapW, xOfLon(f.lon, wrapW));
    const v = { ...v0, x: Math.round(v0.x) };
    viewRef.current = v;
    setView(v);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studioFlat, studioOn, sb.sw, sb.sh, sb.bw, wrapW]);
  // 新建界面收起平面地图时从平常的地图现在的样子变回星球:正中的经线、1 弧度多少像素、正中和赤道在视口里的位置
  useEffect(() => {
    setFlatGeomSource(() => {
      const el = stageRef.current;
      const g = geo.current;
      const v = viewRef.current;
      if (!el || !g.bw || !g.wrap || getProjection() !== 'equirect') return null;
      const r = el.getBoundingClientRect();
      return { lon: getMapCenter(), kpx: (v.k * g.bw) / (2 * Math.PI), cx: r.left + r.width / 2, cy: r.top + v.y + (v.k * r.height) / 2 };
    });
    return () => setFlatGeomSource(null);
  }, []);
  const hlStamp = hl?.stamp;
  /**
   * 编年史跳转时"看得见的地方"的上、下和目标放在哪个高度(舞台坐标):上面留出世界名、提示条,下面留出时间轴;
   * 窄屏:让出底部的卡片和时间轴胶囊(详情卡片开着时是它上方那一截)
   */
  const jumpBand = (H: number): [number, number, number] => {
    if (!narrow) return [80, H - 110, (H - 16) / 2];
    const [t, b] = phoneFree(H, panelOpen);
    return [t + 8, b - 16, (t + b) / 2];
  };
  /**
   * 弯边投影里的编年史跳转:事发地横向不在视野里就转中央经线过去(走短边),纵向不在就上下平移;约 0.4 秒转过去。
   * b = 事发地的外接框(世界坐标)
   */
  const curvedJump = (b: [number, number, number, number], m: MapProj, W: number, H: number) => {
    const g = geo.current;
    const v0 = viewRef.current;
    const sbx = { sw: W, sh: H, bw: box.w, bh: box.h };
    const bx = (b[0] + b[2]) / 2;
    const by = (b[1] + b[3]) / 2;
    const corners: [number, number][] = [
      [b[0], b[1]],
      [b[2], b[1]],
      [b[0], b[3]],
      [b[2], b[3]],
      [bx, by],
      [bx, b[1]],
      [bx, b[3]],
    ];
    const pts = corners.map(([x, y]) => {
      const [mx, my] = projectWorldNear(m, x, y, bx);
      return worldToStage(mx, my, v0, sbx, g.W, g.H);
    });
    const xs = pts.map((p) => p[0]);
    const ys = pts.map((p) => p[1]);
    const [bandT, bandB, midY] = jumpBand(H);
    // 宽屏左边被侧栏卡片、右边被助手面板挡住的那一截不算看得见;转过去以后事发地落在两边中间那一块的正中(按赤道上每度多少像素估)
    const L = sideRoom(W);
    const R = astRoom(W);
    const inX = Math.min(...xs) >= L + 30 && Math.max(...xs) <= W - R - 30;
    const inY = Math.min(...ys) >= bandT && Math.max(...ys) <= bandB;
    if (inX && inY) return;
    const pxPerDeg = v0.k * (box.w / m.W) * m.s * m.def.kx(0) * (Math.PI / 180);
    const dLon = inX ? 0 : wrapLon(lonOfX(bx, g.W) - m.lon0 - (pxPerDeg > 0 ? (L - R) / 2 / pxPerDeg : 0));
    const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    const toY = inY ? v0.y : Math.min(0, Math.max(H - H * v0.k, v0.y + midY - cy));
    if (Math.abs(dLon) < 0.5 && Math.abs(toY - v0.y) < 1) return;
    (window as unknown as { __wfPan: unknown }).__wfPan = { dLon, dy: toY - v0.y, stamp: hlStamp };
    const lon0 = m.lon0;
    const t0 = performance.now();
    let raf = 0;
    setMapMoving(true);
    const step = (now: number) => {
      const t = animProgress(now, t0, 400);
      const e = 1 - (1 - t) ** 3;
      if (dLon) publishMapCenter(wrapLon(lon0 + dLon * e));
      setView(clampRef.current({ k: v0.k, x: v0.x, y: v0.y + (toY - v0.y) * e }, W, H));
      if (t < 1) raf = requestAnimationFrame(step);
      else setMapMoving(false);
    };
    raf = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(raf);
      setMapMoving(false);
    };
  };
  useEffect(() => {
    const el = stageRef.current;
    if (!hl || !data || !civ || !el || civ.regions.of.length !== data.world.mesh.n || getGlobeOn()) return;
    // 照故事找世界标两国:地图自己飞过去看全两国(不在这里另平移,两边同时挪会打架)
    if (getFinder().open && getStage().stage === 'draft') return;
    let b = highlightBox(data.world, civ, highlightMarks(civ, hl));
    if (!b) return;
    const W = el.clientWidth;
    const H = el.clientHeight;
    const v0 = viewRef.current;
    const ww = wrapOf(data.world);
    const m = mpRef.current;
    if (m && box.w) return curvedJump(b, m, W, H);
    // 宽屏左边被侧栏卡片、右边被助手面板挡住的那一截不算看得见,平移到两边中间那一块的正中
    const L = sideRoom(W);
    const R = astRoom(W);
    if (box.w) {
      // 事发地取离看得见那一块的中心最近的那一份 —— 平移走短边(不会绕地球大半圈)
      // 那一块的中心(展开的世界坐标,和 sx 同一套:主图那一份左边起算)
      const c = stageToWorld((L + W - R) / 2, 0, v0, { sw: W, sh: H, bw: box.w, bh: box.h }, ww, 1)[0];
      const bc = (b[0] + b[2]) / 2;
      const sh = nearX(bc, c, ww) - bc;
      b = [b[0] + sh, b[1], b[2] + sh, b[3]];
    }
    // 世界坐标 → 舞台上的屏幕坐标(地图框在舞台里居中,再整体平移 x/y、放大 k)
    const sx = (wx: number) => v0.x + ((W - box.w) / 2 + (wx / data.world.width) * box.w) * v0.k;
    const sy = (wy: number) => v0.y + ((H - box.h) / 2 + (wy / data.world.height) * box.h) * v0.k;
    const x0 = sx(b[0]);
    const x1 = sx(b[2]);
    const y0 = sy(b[1]);
    const y1 = sy(b[3]);
    // 上面留出提示条,下面留出时间轴(窄屏:底部卡片和时间轴胶囊上方)
    const [bandT, bandB, midY] = jumpBand(H);
    if (x0 >= L + 30 && x1 <= W - R - 30 && y0 >= bandT && y1 <= bandB) return;
    const cx = (x0 + x1) / 2;
    const cy = (y0 + y1) / 2;
    // 左右不夹(每一帧再挪整数圈,画面是连着的);上下夹在两极以内
    const to = { k: v0.k, x: v0.x + (L + W - R) / 2 - cx, y: Math.min(0, Math.max(H - H * v0.k, v0.y + midY - cy)) };
    // 事发地差不多在背面时,让开侧栏那一点会让平移超过半圈:东西相连,改走另一边(差一整圈)
    if (box.w) {
      const turn = v0.k * box.w;
      if (to.x - v0.x > turn / 2) to.x -= turn;
      else if (to.x - v0.x < -turn / 2) to.x += turn;
    }
    if (Math.abs(to.x - v0.x) < 1 && Math.abs(to.y - v0.y) < 1) return;
    (window as unknown as { __wfPan: unknown }).__wfPan = { dx: to.x - v0.x, dy: to.y - v0.y, stamp: hlStamp };
    const t0 = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const t = animProgress(now, t0, 400);
      const e = 1 - (1 - t) ** 3;
      const v = { k: v0.k, x: v0.x + (to.x - v0.x) * e, y: v0.y + (to.y - v0.y) * e };
      setView(clampRef.current(v, W, H));
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
    // 只在点了新的一条时平移
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hlStamp]);

  // ---- 选中 → 暂停 + 地图飞过去(国家面板):不管选中来自点地图、面板里的链接、概览还是搜索 ----
  // 国家:平移缩放到能看全当年的疆域,右边让出面板;城 / 州 / 地理实体:平移过去,缩放不变或适度放大;0.6 秒,ease-out 三次方。
  // 地球仪用它自己的 flyTo。选目标时 / 下了令之后缩回整张图('home')
  const flyNow = (to: 'sel' | 'home') => {
    stopFly();
    const el = stageRef.current;
    if (!data || !el || !box.w || replayOn || getTerrainTool().on) return;
    const sel = getSelection().sel;
    const year = civ ? Math.min(civ.endYear, Math.max(0, getCivTime().year ?? civ.endYear)) : 0;
    const focus =
      to === 'sel' && sel && civ
        ? sel.kind === 'mark'
          ? selectedMarkFocus(civ, sel.id)
          : sel.kind === 'character'
            ? selectedCharacterFocus(civ, sel.id)
            : selectionFocus(data.world, civ, sel, year)
        : null;
    if (to === 'sel' && (!focus || !sel)) return;
    // 人物按他的国家飞(看全疆域)
    const goal: FlyGoal = { focus, kind: to === 'sel' && sel ? (sel.kind === 'person' ? 'polity' : sel.kind) : 'home' };
    if (getGlobeOn()) {
      // 作者标记:已经在球的正面、看得见的地方就不转
      if (focus && sel?.kind === 'mark') {
        const p = globeApi.current?.worldToClient(focus.x, focus.y);
        const r = el.getBoundingClientRect();
        if (p && p[0] > r.left + sideRoom(r.width) + 60 && p[0] < r.right - 60 && p[1] > r.top + 80 && p[1] < r.bottom - 110) return;
      }
      if (focus) globeApi.current?.flyTo(focus.lon, focus.lat);
      return;
    }
    const b: StageBox = { sw: el.clientWidth, sh: el.clientHeight, bw: box.w, bh: box.h, padB: geo.current.padB };
    const W = data.world.width;
    const H = data.world.height;
    const m = mpRef.current;
    const flat = m ? null : flatFly(viewRef.current, b, W, H, goal);
    const step = m ? curvedFly(viewRef.current, b, m, (lon) => curvedProj(getProjection(), lon, W, H) ?? m, goal) : flat && ((e: number) => ({ v: flat(e), lon: null }));
    if (!step) return;
    runFly(step, !!m);
  };
  /** 一帧帧飞过去(FLY_MS,ease-out 三次方);用户自己拖动 / 缩放时 stopFly 让给用户(按下地图、滚轮、右下的 + −) */
  const runFly = (step: (e: number) => { v: MapView; lon: number | null }, curvedNow: boolean) => {
    let t0 = -1;
    const frame = (now: number) => {
      // 第一帧地图不动:点选时刚打开的面板先画到屏幕上(反馈不等地图重画),下一帧起飞,时长不变
      if (t0 < 0) {
        t0 = now;
        flyRaf.current = requestAnimationFrame(frame);
        return;
      }
      if (curvedNow) setMapMoving(true);
      const t = animProgress(now, t0, FLY_MS);
      const r = step(easeOutCubic(t));
      if (r.lon !== null) publishMapCenter(wrapLon(r.lon));
      viewRef.current = r.v;
      setView(r.v);
      if (t < 1) flyRaf.current = requestAnimationFrame(frame);
      else stopFly();
    };
    flyRaf.current = requestAnimationFrame(frame);
  };
  /**
   * 导播请地图飞到一段事上(Director.tsx):看全事发地周围几个州,放在字幕条上面那块地方的正中;
   * 事发地已经在那块的中间一半里、缩放也差不多(不到 1.4 倍)就不动。地球仪转过去
   */
  const flyDirector = (focus: Focus) => {
    const el = stageRef.current;
    if (!data || !el || !box.w || replayOn || getTerrainTool().on) return;
    const r = el.getBoundingClientRect();
    const b: StageBox = { sw: el.clientWidth, sh: el.clientHeight, bw: box.w, bh: box.h, padB: geo.current.padB };
    // 看得见的地方:宽屏让开侧栏、助手、顶上的按钮;手机让开收起的世界卡片;都让开时间轴和它上面的字幕条
    const phoneNow = b.sw <= NARROW_MAX;
    const [l, t, rr, bb] = freeArea(b, !phoneNow);
    const row = document.querySelector('.app .bottom-row')?.getBoundingClientRect();
    // 逐年推演停一下:让开"这一段的大事"卡片(宽屏在时间轴上面,手机是底部卡片)
    const card = document.querySelector('.app .sw-review, .app .sw-sheet')?.getBoundingClientRect();
    const capTop = card && card.height ? card.top - r.top - 12 : row && row.height ? row.top - r.top - (phoneNow ? 115 : 100) : bb;
    const area: [number, number, number, number] = [l, t, rr, Math.max(t + 80, Math.min(bb, capTop))];
    const near = (p: [number, number] | null | undefined) => {
      if (!p) return false;
      const x = p[0] - r.left;
      const y = p[1] - r.top;
      const qw = (area[2] - area[0]) / 4;
      const qh = (area[3] - area[1]) / 4;
      return x > area[0] + qw && x < area[2] - qw && y > area[1] + qh && y < area[3] - qh;
    };
    if (getGlobeOn()) {
      if (!near(globeApi.current?.worldToClient(focus.x, focus.y))) globeApi.current?.flyTo(focus.lon, focus.lat);
      return;
    }
    stopFly();
    const goal: FlyGoal = { focus, kind: 'polity' };
    const W = data.world.width;
    const H = data.world.height;
    const m = mpRef.current;
    const flat = m ? null : flatFly(viewRef.current, b, W, H, goal, area);
    const step = m ? curvedFly(viewRef.current, b, m, (lon) => curvedProj(getProjection(), lon, W, H) ?? m, goal, area) : flat && ((e: number) => ({ v: flat(e), lon: null }));
    if (!step) return;
    const k = step(1).v.k / viewRef.current.k;
    if (k < 1.4 && k > 1 / 1.4 && near(worldToClient.current?.(focus.x, focus.y))) return;
    runFly(step, !!m);
  };
  const flyDirectorRef = useRef(flyDirector);
  flyDirectorRef.current = flyDirector;
  const directorFly = useDirectorFly();
  const directorOnPref = useDirectorOn();
  const civStory = useCivStory();
  useEffect(() => {
    if (directorFly) flyDirectorRef.current(directorFly.focus);
  }, [directorFly]);
  /** 选中的作者标记(正在填的那一份优先:新建的还没存)在地图上的位置 */
  const selectedMarkFocus = (civ: Civ, id: number) => {
    if (!data) return null;
    const d = getMarkUi().draft;
    if (d && d.id === id) return markFocus(data.world, civ, d.scope === 'point' ? { at: d.at ?? undefined } : { regions: d.regions });
    const m = getEdits().marks?.find((x) => x.id === id);
    return m ? markFocus(data.world, civ, m) : null;
  };
  /** 选中的作者人物(正在填的那一份优先)一生去过的地方的范围 */
  const selectedCharacterFocus = (civ: Civ, id: number) => {
    if (!data) return null;
    const d = getCharUi().draft;
    const year = Math.min(civ.endYear, Math.max(0, getCivTime().year ?? civ.endYear));
    const c = d && d.id === id ? draftAsCharacter(d, year) : getEdits().characters?.find((x) => x.id === id);
    if (!c) return null;
    const pts = lifeStops(c)
      .map((s) => placeOf(civ, data.world, data.raster, s.where, s.year).at)
      .filter((p): p is [number, number] => !!p);
    return pointsFocus(data.world, pts);
  };
  const flyRef = useRef(flyNow);
  flyRef.current = flyNow;
  useEffect(() => () => stopFly(), []);

  // ---- 分享链接的"这一刻"(shareMoment.tsx、gen/savefile.ts 的 SaveMoment):复制时取下现在的,打开时照它停好 ----
  /**
   * 现在的镜头:看得见的那一块(宽屏让开侧栏;手机让开底部卡片和胶囊,见 flyTo.ts 的 freeArea)正中的经纬度,
   * 放大倍数按宽度算(整圈经线正好占满画面的宽 = 1;电脑发给手机,横着看到的差不多一样宽)。地球仪:球心的经纬度、它自己的倍数
   */
  const cameraNow = (): SaveCamera | null => {
    if (getGlobeOn()) {
      const c = globeApi.current?.camera();
      return c ? cleanCamera({ lon: c.lon, lat: c.lat, zoom: c.k }) : null;
    }
    const el = stageRef.current;
    const g = geo.current;
    if (!el || !g.bw || !dataRef.current) return null;
    const b: StageBox = { sw: el.clientWidth, sh: el.clientHeight, bw: g.bw, bh: g.bh, padB: g.padB };
    const [l, t, r, btm] = freeArea(b, panelOpenRef.current);
    const v = viewRef.current;
    let [x, y] = stageToWorld((l + r) / 2, (t + btm) / 2, v, b, g.W, g.H);
    const m = mpRef.current;
    if (m) {
      const u = unprojectWorld(m, x, y);
      [x, y] = u ?? [xOfLon(getMapCenter(), g.W), g.H / 2];
    }
    return cleanCamera({ lon: lonOfX(x, g.W), lat: 90 - (y / g.H) * 180, zoom: (v.k * g.bw) / b.sw });
  };
  /** 镜头飞到分享的人那时的样子(倍数换算成这块屏幕的,夹在能放的范围里);地球仪还没出来就等它出来 */
  const flyCamera = (cam: SaveCamera, tries = 0) => {
    stopFly();
    const el = stageRef.current;
    if (!data || !el || !box.w || replayOn) return;
    if (getGlobeOn()) {
      const api = globeApi.current;
      if (api?.viewSig()) return api.flyTo(cam.lon, cam.lat, cam.zoom);
      if (tries < 120) requestAnimationFrame(() => flyCameraRef.current(cam, tries + 1));
      return;
    }
    const b: StageBox = { sw: el.clientWidth, sh: el.clientHeight, bw: box.w, bh: box.h, padB: geo.current.padB };
    const W = data.world.width;
    const H = data.world.height;
    const x = xOfLon(cam.lon, W);
    const y = ((90 - cam.lat) / 180) * H;
    const goal: FlyGoal = { focus: { box: null, x, y, lon: cam.lon, lat: cam.lat }, kind: 'polity', zoom: Math.min(12, Math.max(1, (cam.zoom * b.sw) / b.bw)) };
    const area = freeArea(b, panelOpenRef.current);
    const m = mpRef.current;
    const flat = m ? null : flatFly(viewRef.current, b, W, H, goal, area);
    const step = m ? curvedFly(viewRef.current, b, m, (lon) => curvedProj(getProjection(), lon, W, H) ?? m, goal, area) : flat && ((e: number) => ({ v: flat(e), lon: null }));
    if (step) runFly(step, !!m);
  };
  const flyCameraRef = useRef(flyCamera);
  flyCameraRef.current = flyCamera;
  /**
   * 照故事找世界:地图飞过去看全这几个点(故事里两国的州、隘口、交界)。where = 'finder' 让开找世界的卡片(电脑左边、手机底部卡片),
   * 'world' 照平常的侧栏让;zoom = 只飞到一个点时放大几倍
   */
  const flyToPoints = (pts: readonly (readonly [number, number])[], where: 'finder' | 'world', zoom?: number) => {
    stopFly();
    const el = stageRef.current;
    if (!data || !el || !box.w || replayOn) return;
    const focus = pointsFocus(data.world, pts);
    if (!focus) return;
    if (getGlobeOn()) return globeApi.current?.flyTo(focus.lon, focus.lat);
    const b: StageBox = { sw: el.clientWidth, sh: el.clientHeight, bw: box.w, bh: box.h, padB: geo.current.padB };
    const W = data.world.width;
    const H = data.world.height;
    const phoneNow = b.sw <= NARROW_MAX;
    const area: [number, number, number, number] =
      where === 'world' ? freeArea(b, false) : phoneNow ? [12, 56, b.sw - 12, Math.round(b.sh * 0.5) - 10] : [448, 64, b.sw - 24, b.sh - 24];
    const goal: FlyGoal = { focus, kind: 'polity', ...(zoom ? { zoom } : {}) };
    const m = mpRef.current;
    const flat = m ? null : flatFly(viewRef.current, b, W, H, goal, area);
    const step = m ? curvedFly(viewRef.current, b, m, (lon) => curvedProj(getProjection(), lon, W, H) ?? m, goal, area) : flat && ((e: number) => ({ v: flat(e), lon: null }));
    if (step) runFly(step, !!m);
  };
  const panelOpenRef = useRef(panelOpen);
  panelOpenRef.current = panelOpen;
  /** 打开带"这一刻"的分享链接:要停到的那一刻(画面出来、历史重推完以后用掉) */
  const pendingMoment = useRef<{ id: string; moment: SaveMoment } | null>(null);
  const [momentTick, setMomentTick] = useState(0);
  /** 照"这一刻"选中时,选中以后镜头飞到这里(不按选中的国家另飞) */
  const momentCam = useRef<SaveCamera | null>(null);
  useEffect(() => {
    const pm = pendingMoment.current;
    // 带着干预、逐年推演的进度的世界:生成完还要重推一次(resimInfo),推完再停(逐年推演的推完会把时间轴放到"现在")
    // 正在回放世界形成:放完再停(放完会接着放文明,停的那一年要在它后面设)
    if (!pm || !data || !rawCiv || !box.w || !stageSize.w || resimInfo.current || replayOn) return;
    pendingMoment.current = null;
    if (currentWorld()?.id !== pm.id) return;
    // 对到这个世界上:年份超出这段历史、国家或州找不到(生成器换了版本)的那一样不管;有地形大事的按那一年那一段的州认
    const y = pm.moment.year;
    const rm = resolveMoment(y !== undefined && rawCiv.eras?.length ? civAtEra(rawCiv, eraIndex(rawCiv, Math.min(y, rawCiv.endYear))) : rawCiv, pm.moment);
    setSharedFor((s) => (s && s.id === pm.id ? { ...s, at: rm.year !== undefined ? { year: rm.year, sel: rm.selected ?? null } : null } : s));
    if (rm.year !== undefined) setCivTime({ year: rm.year, playing: false, scrubbing: false, story: false });
    const sel: MapSelection | null = rm.selected ?? null;
    if (sel && !sameSelection(sel, getSelection().sel)) {
      momentCam.current = rm.camera ?? null;
      setSelection(sel);
      return;
    }
    // 分享的人那时没选中东西(或者对不上):这边原来选着的也收起来(地址栏里又贴了一个链接、还是这张图时会留着)
    if (!sel) clearSelection();
    if (rm.camera) flyCamera(rm.camera);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, rawCiv, box.w, stageSize.w, resim, momentTick, replayOn]);
  /** 复制分享链接时的"这一刻":时间轴那一年、选中的国家或州(withSelection)、镜头 */
  const momentRef = useRef<(withSelection: boolean) => MomentNow | null>(() => null);
  momentRef.current = (withSelection) => {
    const c = civ;
    // 助手"先在地图上看看"时,地图上是试推演的历史,存档里还是原来的;正在重推历史时,地图上还是旧的那份:都不带这一刻(年份、国家对不上)
    if (!c || !c.viable || !shownRaw || previewRaw || resimInfo.current || !dataRef.current || getStage().stage !== 'world') return null;
    const year = Math.min(c.endYear, Math.max(0, getCivTime().year ?? c.endYear));
    const moment: SaveMoment = { year };
    let name: string | null = null;
    const sel = withSelection ? getSelection().sel : null;
    if (sel && (sel.kind === 'polity' || sel.kind === 'region')) {
      const key = selectionKey(shownRaw, sel);
      const p = sel.kind === 'polity' ? c.polities[sel.id] : null;
      if (key) {
        moment.selected = key;
        name = p ? polityName(p, shownYearOf(p, year, c.endYear)) : regionLabel(c, sel.id);
      }
    }
    const camera = cameraNow();
    if (camera) moment.camera = camera;
    return { moment, year: yearFull(year, getEdits().era), name };
  };
  useEffect(() => {
    setMomentSource((withSelection) => momentRef.current(withSelection));
    return () => setMomentSource(null);
  }, []);
  // 按稳定键认"选中的是不是换了":重推历史后编号变了、还是同一个东西,不再飞
  const selStable = shownRaw && selState.sel ? selectionKey(shownRaw, selState.sel) : '';
  useEffect(() => {
    if (!selStable) return;
    pausePlayback();
    // 打开带"这一刻"的分享链接时的选中:镜头照分享的人的,不按选中的国家另飞
    const cam = momentCam.current;
    momentCam.current = null;
    if (cam) return flyCameraRef.current(cam);
    flyRef.current('sel');
  }, [selStable]);
  const flyReq = panelUi.fly;
  useEffect(() => {
    if (flyReq) flyRef.current(flyReq.to);
  }, [flyReq]);

  /** 这次按下以后拖动过(拖过就不算单击,不选中) */
  const moved = useRef(false);
  // ---- 手指(触屏):单指拖动平移、双指捏合缩放(以两指中点为中心)、点一下 = 单击、点两下 = 回正 ----
  /** 按在地图上的手指(id → 屏幕坐标;地球仪上的也记,双击回正用) */
  const touches = useRef(new Map<number, Pt>());
  /** 双指捏合:上一次用到的两指位置;手指移动先记下,下一帧一起缩放 / 平移(一帧最多一次) */
  const pinch = useRef<{ a: Pt; b: Pt; raf: number } | null>(null);
  /** 改地形正用手指画线(这时第二根手指不捏合) */
  const terrainStroke = useRef(false);
  /** 正在画的那一笔是哪根手指 / 哪个指针按下的:别的手指的移动、松开不算进这一笔 */
  const terrainPointer = useRef<number | null>(null);
  /** 这一下手指按下的位置、时刻(松手时判断是不是"点一下");中途多了一根手指就不算 */
  const tapStart = useRef<(Tap & { id: number; multi: boolean }) | null>(null);
  /** 上一下"点一下"(和这一下够近就是双击) */
  const lastTap = useRef<Tap | null>(null);
  /** 刚被手指双击过(时刻):紧跟着的 click 按双击的第二下处理(恢复原来的选中) */
  const dblTapAt = useRef(-1e9);
  /** 平移(屏幕像素);弯边投影左右 = 转中央经线 */
  const panBy = (dx: number, dy: number) => {
    const el = stageRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const m = mpRef.current;
    const g = geo.current;
    if (m && g.bw) {
      const v = viewRef.current;
      const pxPerDeg = v.k * (g.bw / m.W) * m.s * m.def.kx(0) * (Math.PI / 180);
      if (pxPerDeg > 0 && dx) publishMapCenter(wrapLon(getMapCenter() - dx / pxPerDeg));
      const nv = clampRef.current({ k: v.k, x: v.x, y: v.y + dy }, rect.width, rect.height);
      viewRef.current = nv;
      setView(nv);
      return;
    }
    setView((v) => clampRef.current({ k: v.k, x: v.x + dx, y: v.y + dy }, rect.width, rect.height));
  };
  const startPinch = () => {
    const [a, b] = [...touches.current.values()];
    if (!a || !b) return;
    drag.current = null;
    moved.current = true;
    setHover(null);
    // 单指拖动时排着的"转中央经线"作废(不然下一帧把捏合的结果盖掉)
    const c = centerFrame.current;
    cancelAnimationFrame(c.raf);
    c.raf = 0;
    c.lon = null;
    if (pinch.current) cancelAnimationFrame(pinch.current.raf);
    pinch.current = { a: { ...a }, b: { ...b }, raf: 0 };
    if (curvedRef.current) setMapMoving(true);
  };
  const schedulePinch = () => {
    const p = pinch.current;
    if (!p || p.raf) return;
    p.raf = requestAnimationFrame(() => {
      p.raf = 0;
      if (pinch.current !== p) return;
      const [a, b] = [...touches.current.values()];
      const el = stageRef.current;
      if (!a || !b || !el) return;
      const st = pinchStep(p.a, p.b, a, b);
      p.a = { ...a };
      p.b = { ...b };
      const r = el.getBoundingClientRect();
      // 先以上一帧的中点为中心缩放,再跟着中点平移:两指下面的地方一直在两指下面
      if (Math.abs(st.f - 1) > 1e-4) zoomRef.current(st.mx - st.dx - r.left, st.my - st.dy - r.top, st.f);
      if (st.dx || st.dy) panBy(st.dx, st.dy);
    });
  };
  /** 捏合结束:还剩一根手指就接着单指拖动 */
  const endPinch = () => {
    const p = pinch.current;
    if (!p) return;
    cancelAnimationFrame(p.raf);
    pinch.current = null;
    const [rest] = [...touches.current.values()];
    if (rest) {
      const v = viewRef.current;
      drag.current = { x: rest.x, y: rest.y, vx: v.x, vy: v.y, lon: getMapCenter(), touch: true };
      return;
    }
    drag.current = null;
    setMapMoving(false);
  };
  // 手指的登记放在捕获阶段(地球仪自己的处理会拦住冒泡):哪几根手指按着、是不是"点一下"、双击回正
  const onTouchDownCapture = (e: React.PointerEvent) => {
    if (e.pointerType !== 'touch') return;
    touches.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (touches.current.size === 1) tapStart.current = { id: e.pointerId, x: e.clientX, y: e.clientY, t: performance.now(), multi: false };
    else if (tapStart.current) tapStart.current.multi = true;
  };
  const onTouchMoveCapture = (e: React.PointerEvent) => {
    if (e.pointerType === 'touch' && touches.current.has(e.pointerId)) touches.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
  };
  const onTouchUpCapture = (e: React.PointerEvent) => {
    if (e.pointerType !== 'touch') return;
    touches.current.delete(e.pointerId);
    const ts = tapStart.current;
    if (!ts || ts.id !== e.pointerId) return;
    tapStart.current = null;
    const now = performance.now();
    const onMap = !!(e.target as HTMLElement | null)?.closest?.('.canvas-wrap, .globe');
    if (e.type !== 'pointerup' || ts.multi || !onMap || now - ts.t > 500 || Math.hypot(e.clientX - ts.x, e.clientY - ts.y) > TOUCH_SLOP) {
      lastTap.current = null;
      return;
    }
    const tap: Tap = { x: e.clientX, y: e.clientY, t: now };
    if (!isDoubleTap(lastTap.current, tap)) {
      lastTap.current = tap;
      return;
    }
    // 点两下:回正(和鼠标双击一样;浏览器自己也发了 dblclick 的话再回正一次也不要紧)
    lastTap.current = null;
    dblTapAt.current = now;
    if (getGlobeOn()) globeApi.current?.reset();
    else resetView();
  };
  const onPointerDown = (e: React.PointerEvent) => {
    touchRef.current();
    stopFly();
    if (getGlobeOn()) return; // 地球仪自己管拖动
    const touch = e.pointerType === 'touch';
    // 第二根手指:开始捏合(编辑地形刚按下第一根手指就跟上第二根 = 想捏合,那一笔不算;已经画了一阵的不管)
    if (touch && touches.current.size >= 2) {
      if (terrainStroke.current) {
        if (!(getUpUi().on ? upCancel() : terrainCancel())) return;
        terrainStroke.current = false;
        terrainPointer.current = null;
      }
      if (touches.current.size === 2) startPinch();
      return;
    }
    // 改地形:画线的工具按下就开始画(不平移);点地图收菜单的那一下不画
    if (!dismissing(e.nativeEvent) && (terrainDown(worldAt(e.clientX, e.clientY), e.button) || upDown(worldAt(e.clientX, e.clientY), e.button))) {
      moved.current = true;
      terrainStroke.current = touch;
      terrainPointer.current = e.pointerId;
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
      return;
    }
    if (e.button !== 0) return; // 只用左键
    drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, lon: getMapCenter(), touch };
    moved.current = false;
    if (stageRef.current) stageRef.current.style.cursor = '';
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };
  /**
   * 屏幕坐标 → 主图上的像素(不在地图上 = null)。
   * 视窗外面(宽屏两边的空白)不算;主图右边接的那一份、跨过 180° 经线的地方按列取模 —— 接缝两边点到的是同一块地
   */
  const pixelAt = (cx: number, cy: number): [number, number] | null => {
    if (getGlobeOn()) return data ? (globeApi.current?.pixelAt(cx, cy) ?? null) : null;
    if (!data || !canvasRef.current) return null;
    if (mp) {
      // 弯边投影:屏幕 → 地图平面 → 反投影回世界坐标(外轮廓外面 = 不在地图上)
      const w = worldAt(cx, cy);
      if (!w) return null;
      const s = data.raster.scale;
      return [Math.min(data.raster.w - 1, Math.floor(w[0] * s)), Math.min(data.raster.h - 1, Math.floor(w[1] * s))];
    }
    const cr = canvasRef.current.getBoundingClientRect();
    let px = Math.floor(((cx - cr.left) / cr.width) * data.raster.w);
    const py = Math.floor(((cy - cr.top) / cr.height) * data.raster.h);
    if (!inWindow(cx)) return null;
    px = ((px % data.raster.w) + data.raster.w) % data.raster.w;
    if (px < 0 || py < 0 || px >= data.raster.w || py >= data.raster.h) return null;
    return [px, py];
  };
  /** 屏幕上这一点在不在视窗(外框 ∩ 舞台)里 */
  const inWindow = (cx: number): boolean => {
    const el = stageRef.current;
    if (!el || !box.w) return false;
    const r = el.getBoundingClientRect();
    const [wl, wr] = windowSpan(view.k, { sw: r.width, sh: r.height, bw: box.w, bh: box.h });
    return cx - r.left >= wl && cx - r.left <= wr;
  };
  /** 屏幕坐标 → 地块(不在地图上 = −1) */
  const cellAt = (cx: number, cy: number): number => {
    const p = pixelAt(cx, cy);
    return p && data ? data.raster.cell[p[1] * data.raster.w + p[0]] : -1;
  };
  /**
   * 屏幕坐标 → 世界坐标(地图原图的像素坐标;不在地图上 = null)。
   * x 取模到 [0, 宽)(改地形画线时由 TerrainTools 按上一个点展开,跨接缝的线是连着的一笔)
   */
  const worldAt = (cx: number, cy: number): [number, number] | null => {
    if (!data || !canvasRef.current) return null;
    const cr = canvasRef.current.getBoundingClientRect();
    let u = (cx - cr.left) / cr.width;
    const v = (cy - cr.top) / cr.height;
    if (!inWindow(cx)) return null;
    if (mp) {
      if (!(u >= 0 && v >= 0 && u <= 1 && v <= 1)) return null;
      return unprojectWorld(mp, u * data.world.width, v * data.world.height);
    }
    u -= Math.floor(u);
    if (!(u >= 0 && v >= 0 && u <= 1 && v <= 1)) return null;
    return [u * data.world.width, v * data.world.height];
  };
  // ---- 作者标记(MarkLayer.tsx 画、markStore.ts 管放标记和正在填的那一份) ----
  /** 屏幕坐标 → 世界坐标(地球仪按球上的像素;不在地图上 = null) */
  const markWorldAt = (cx: number, cy: number): [number, number] | null => {
    if (!data) return null;
    if (getGlobeOn()) {
      const p = globeApi.current?.pixelAt(cx, cy);
      const sc = data.raster.scale;
      return p ? [(p[0] + 0.5) / sc, (p[1] + 0.5) / sc] : null;
    }
    return worldAt(cx, cy);
  };
  /** 屏幕坐标 → 州号(海上、地图外 = −1) */
  const regionAtClient = (cx: number, cy: number): number => {
    const c = cellAt(cx, cy);
    return civ && c >= 0 && c < civ.regions.of.length ? civ.regions.of[c] : -1;
  };
  const markApi = useRef<MarkApi | null>(null);
  markApi.current = {
    // 世界坐标 → 舞台坐标:平面主图(左右相连,按视窗裁)、弯边投影、地球仪
    frame: () => {
      const el = stageRef.current;
      const g = geo.current;
      if (!el || !g.bw) return null;
      const r = el.getBoundingClientRect();
      const at = `${r.left},${r.top},${r.width},${r.height}`;
      const base = { left: r.left, top: r.top, w: r.width, h: r.height };
      if (getGlobeOn()) {
        const ga = globeApi.current;
        const gv = ga?.viewSig();
        if (!ga || !gv) return null;
        const pt = (wx: number, wy: number): [number, number] | null => {
          const p = ga.worldToClient(wx, wy);
          return p ? [p[0] - r.left, p[1] - r.top] : null;
        };
        return { ...base, pt, period: 0, win: [0, r.width], k: gv.k, cut: 0, sig: `g|${gv.sig}|${at}` };
      }
      const b = { sw: r.width, sh: r.height, bw: g.bw, bh: g.bh };
      const v = viewRef.current;
      const m = mpRef.current;
      const sig = `${m?.key ?? 'f'}|${v.k},${v.x},${v.y}|${at}|${g.bw},${g.bh}`;
      if (m) {
        const pt = (wx: number, wy: number): [number, number] => {
          const [x, y] = projectWorld(m, wx, wy);
          return worldToStage(x, y, v, b, g.W, g.H);
        };
        return { ...base, pt, period: 0, win: [0, r.width], k: v.k, mapCss: g.bw, cut: 0.4 * g.bw * v.k, sig };
      }
      const pt = (wx: number, wy: number) => worldToStage(wx, wy, v, b, g.W, g.H);
      return { ...base, pt, period: g.wrap ? (g.wrap / g.W) * g.bw * v.k : 0, win: g.wrap ? windowSpan(v.k, b) : [0, r.width], k: v.k, mapCss: g.bw, cut: 0, sig };
    },
    regionAt: regionAtClient,
    onMap: (cx, cy) => !!pixelAt(cx, cy),
    // 地球仪上的字另画,不躲
    textBoxes: () => (getGlobeOn() ? { ver: -1, list: [] } : mapTextBoxes()),
  };
  /** 这一年(时间轴当前那年,取整) */
  const markYear = () => (civ ? Math.floor(Math.min(civ.endYear, Math.max(0, getCivTime().year ?? civ.endYear))) : 0);
  /**
   * 悬停时标记要说的:放标记、圈州时写鼠标下是哪(海上也行);正在填一个点的标记时图钉上是"能拖"的光标;
   * 停在地图上的标记上 = 它的名字和年份(停在图钉、名字上时 tip = 图钉尖,小卡片放在它左上方;圈州时小卡片放在鼠标左边)。
   * info 不给 = 照常的悬停小卡片;整个不归标记管 = null
   */
  const markHoverAt = (cx: number, cy: number): { info?: HoverInfo | null; cursor: string; tip?: [number, number] | null; left?: boolean } | null => {
    if (!civ || !data) return null;
    const mk = getMarkUi();
    const year = markYear();
    const owner = (r: number) => ownerName(civ, ownersAt(civ, year).polity[r], year);
    if (mk.placing || mk.draft?.scope === 'regions') {
      const w = markWorldAt(cx, cy);
      if (!w) return { info: null, cursor: '' };
      const r = regionAtClient(cx, cy);
      if (mk.placing) {
        const name = r >= 0 ? regionLabel(civ, r) : (markSpot(civ, data.world, data.raster, w, year).sea ?? '海上');
        return { info: { name, sub: r >= 0 ? owner(r) : undefined, extra: '点一下，在这里放标记' }, cursor: 'none' };
      }
      if (r < 0) return { info: null, cursor: '' };
      const on = mk.draft!.regions.includes(regionKey(civ, r));
      return { info: { name: regionLabel(civ, r), sub: owner(r), extra: on ? '再点一下去掉' : '点一下加进来' }, cursor: 'pointer', left: true };
    }
    if (mk.draft) return markPinAt(cx, cy, mk.draft.id) ? { info: null, cursor: 'grab' } : { cursor: 'crosshair' };
    const hit = markHitAt(cx, cy);
    if (!hit) return null;
    if (hit.kind === 'cluster') return { info: null, cursor: 'zoom-in' };
    const m = getEdits().marks?.find((x) => x.id === hit.ids[0]);
    return m ? { info: markHover(m), cursor: 'pointer', tip: hit.kind === 'pill' ? null : markPinTip(m.id) } : null;
  };
  /** 挑地方时点地图得到的地方:城镇符号、城名 = 那座城;陆地 = 那一州;海上 = 那一点 */
  const whereAtClient = (cx: number, cy: number): Where | null => {
    if (!civ) return null;
    const hit = labelAt(cx, cy);
    if (hit?.kind === 'settlement' && civ.settlements[hit.id]) return whereOfCity(civ, hit.id);
    const r = regionAtClient(cx, cy);
    if (r >= 0) return whereOfRegion(civ, r);
    return markWorldAt(cx, cy);
  };
  /**
   * 悬停时作者的人物要说的:挑地方时写鼠标下是哪(那一年归谁);停在地图上的头像上 = 名字、那年多大、在哪。
   * 不归人物管 = null(再看标记的)
   */
  const charHoverAt = (cx: number, cy: number): { info?: HoverInfo | null; cursor: string; tip?: [number, number] | null; left?: boolean } | null => {
    if (!civ || !data) return null;
    const cu = getCharUi();
    if (cu.picking && cu.draft) {
      const w = whereAtClient(cx, cy);
      if (!w) return { info: null, cursor: '' };
      const t = cu.picking === 'birth' ? cu.draft.bornText : cu.draft.sub?.kind === 'life' ? cu.draft.sub.d.yearText : '';
      const ty = parseCharYear(t);
      const year = ty === null || Number.isNaN(ty) ? markYear() : ty;
      const pl = placeOf(civ, data.world, data.raster, w, year);
      const sub = pl.region !== undefined ? ownerName(civ, ownersAt(civ, Math.min(civ.endYear, year)).polity[pl.region], year) : undefined;
      return { info: { name: pl.name, sub, extra: '点一下，选这里' }, cursor: 'none' };
    }
    const id = characterPinAt(cx, cy);
    if (id === null) return null;
    const c = getEdits().characters?.find((x) => x.id === id);
    return c ? { info: characterHover(civ, data.world, data.raster, c, markYear()), cursor: 'pointer', tip: characterPinTip() } : { info: null, cursor: 'pointer' };
  };
  /** 标记说的悬停小卡片(有图钉尖就放在图钉左上方,圈州时放在鼠标左边) */
  const markHoverCard = (mh: { info?: HoverInfo | null; tip?: [number, number] | null; left?: boolean }, x: number, y: number) =>
    setHover(mh.info ? (mh.tip ? { info: mh.info, x: mh.tip[0], y: mh.tip[1], place: 'above' } : { info: mh.info, x, y, place: mh.left ? 'left' : undefined }) : null);
  /** 正在拖的图钉(按下的那根手指 / 鼠标);松手的时刻(紧跟着的 click 不算点地图) */
  const pinDrag = useRef<number | null>(null);
  const pinDragEnd = useRef(-1e9);
  // 按在正在填的标记的图钉上:拖图钉(捕获阶段:地图、地球仪都不拖)
  const onMarkDownCapture = (e: React.PointerEvent) => {
    const d = getMarkUi().draft;
    if (!d || d.scope !== 'point' || !d.at || replayOn || (e.pointerType === 'mouse' && e.button !== 0) || touches.current.size > 1) return;
    if (!markPinAt(e.clientX, e.clientY, d.id)) return;
    e.stopPropagation();
    stopFly();
    pinDrag.current = e.pointerId;
    setMarkDragging(true);
    setHover(null);
    if (stageRef.current) stageRef.current.style.cursor = 'grabbing';
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onMarkMoveCapture = (e: React.PointerEvent): boolean => {
    if (pinDrag.current !== e.pointerId) return false;
    e.stopPropagation();
    const w = markWorldAt(e.clientX, e.clientY);
    if (w) patchDraft({ at: w });
    return true;
  };
  const onMarkUpCapture = (e: React.PointerEvent) => {
    if (pinDrag.current !== e.pointerId) return;
    e.stopPropagation();
    pinDrag.current = null;
    pinDragEnd.current = performance.now();
    setMarkDragging(false);
    if (stageRef.current) stageRef.current.style.cursor = '';
  };
  /** 点到合并的圆:以它为中心放大到写名字的程度(至少 1.6 倍) */
  const zoomToCluster = (cx: number, cy: number) => {
    const el = stageRef.current;
    if (!el) return;
    const k = getGlobeOn() ? (globeApi.current?.viewSig()?.k ?? 1) : viewRef.current.k;
    const f = Math.max(1.6, (NAME_ZOOM * 1.05) / k);
    if (getGlobeOn()) return globeApi.current?.zoomBy(f, cx, cy);
    const r = el.getBoundingClientRect();
    zoomAt(cx - r.left, cy - r.top, f);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    const el = stageRef.current;
    if (!el || getGlobeOn()) return;
    // 双指捏合:等下一帧一起算
    if (pinch.current) {
      if (e.pointerType === 'touch') schedulePinch();
      return;
    }
    const rect = el.getBoundingClientRect();
    if (terrainPointer.current === null || e.pointerId === terrainPointer.current) {
      terrainMove(worldAt(e.clientX, e.clientY));
      upMove(worldAt(e.clientX, e.clientY));
    }
    let label: ReturnType<typeof pickLabelAt> = null;
    let mh: ReturnType<typeof markHoverAt> = null;
    if (drag.current) {
      const d = drag.current;
      if (Math.abs(e.clientX - d.x) + Math.abs(e.clientY - d.y) > (d.touch ? TOUCH_SLOP : CLICK_SLOP)) moved.current = true;
      if (mp && box.w) {
        // 弯边投影:左右拖 = 转中央经线(赤道上的地方跟着鼠标走),上下拖 = 平移。
        // 移动没超过点击的容差前不转:还算"点一下"时转了中心,停着的那一版就得按投影整张重画(几百毫秒),马上又被拖动盖掉
        if (moved.current) {
          setMapMoving(true);
          const pxPerDeg = view.k * (box.w / mp.W) * mp.s * mp.def.kx(0) * (Math.PI / 180);
          if (pxPerDeg > 0) scheduleCenter(d.lon - (e.clientX - d.x) / pxPerDeg);
        }
        setView((v) => clampRef.current({ k: v.k, x: v.x, y: d.vy + e.clientY - d.y }, rect.width, rect.height));
      } else setView((v) => clampRef.current({ k: v.k, x: d.vx + e.clientX - d.x, y: d.vy + e.clientY - d.y }, rect.width, rect.height));
    } else {
      // 鼠标停在能点的字 / 城镇符号上:手指光标(改地形时不管字);作者标记上 / 放标记 / 圈州时按标记的
      const tool = getTerrainTool().on || getUpUi().on;
      label = tool || draft ? null : pickLabelAt(e.clientX, e.clientY);
      mh = tool || draft || replayOn ? null : (charHoverAt(e.clientX, e.clientY) ?? markHoverAt(e.clientX, e.clientY));
      el.style.cursor = mh ? mh.cursor : label ? 'pointer' : '';
    }
    // 悬停小卡片:拖动、改地形、回放、新建时不显示;手指没有"悬停"(点了直接出面板)
    if (!data || (drag.current && moved.current) || getTerrainTool().on || getUpUi().on || replayOn || draft || e.pointerType === 'touch') return setHover(null);
    if (mh && mh.info !== undefined) return markHoverCard(mh, e.clientX, e.clientY);
    const p = pixelAt(e.clientX, e.clientY);
    if (!p) return setHover(null);
    showHover(p, label, e.clientX, e.clientY);
  };
  const probeRef = useRef<(cx: number, cy: number) => string[] | null>(() => null);
  probeRef.current = (cx, cy) => {
    const p = pixelAt(cx, cy);
    return p && data ? probeLines(data.world, data.raster, civ, p[0], p[1]) : null;
  };
  const showHover = (p: [number, number], label: ReturnType<typeof pickLabelAt>, x: number, y: number) => {
    if (!data) return;
    const info = hoverInfo({ world: data.world, raster: data.raster, civ, px: p[0], py: p[1], layer: { style, data: layer, ...fillShow(mapFill) }, label, year: getCivTime().year });
    setHover(info ? { info, x, y } : null);
  };
  const onPointerUp = (e: React.PointerEvent) => {
    if (getGlobeOn()) return;
    if (pinch.current) {
      // 还有两根手指按着(第三根松开了):接着捏合;否则结束捏合,剩下的一根接着拖
      if (touches.current.size >= 2) startPinch();
      else endPinch();
      return;
    }
    // 捏合以后剩下的那根手指:别的手指松开时不结束它的拖动
    if (e.pointerType === 'touch' && drag.current?.touch && touches.current.size > 0) return;
    // 正在画的那一笔:只认按下它的那根手指松开
    if (terrainPointer.current !== null && e.pointerId !== terrainPointer.current) return;
    terrainPointer.current = null;
    terrainUp();
    upUp();
    terrainStroke.current = false;
    drag.current = null;
    setMapMoving(false);
  };
  /** 双击:缩放复位(中央经线不变 —— 它是这个世界的设置,拖远了、放大了双击回到整张图) */
  const resetView = () => {
    const el = stageRef.current;
    if (!el || !box.w) return setView({ k: 1, x: 0, y: 0 });
    const b = { sw: el.clientWidth, sh: el.clientHeight, bw: box.w, bh: box.h };
    const base = { k: 1, x: 0, y: 0 };
    setView(curved || !wrapW ? clampCurved(base, b) : viewCentredAt(base, b, wrapW, xOfLon(getMapCenter(), wrapW)));
  };
  // 改地形只在等距圆柱主图上改:地球仪、弯边投影里打开改地形就先切回等距圆柱(中心不变,地球仪的接上它正对着的经度);
  // 改地形时换成别的投影 = 收起改地形
  useEffect(() => {
    if (terrainTool.on && getProjection() !== 'equirect') setProjection('equirect');
  }, [terrainTool.on]);
  useEffect(() => {
    if (projection !== 'equirect' && getTerrainTool().on) setTerrainTool({ on: false });
    if (projection !== 'equirect' && getUpUi().on) closeUpheaval();
  }, [projection]);
  // 地形大事同样只在等距圆柱主图上放、涂:打开时先切回等距圆柱;打开时详情、选目标、放标记、改地形一起收起
  useEffect(() => {
    if (!upOn) return;
    if (getProjection() !== 'equirect') setProjection('equirect');
    setSheet('half');
    clearSelection();
    setPolityPick(null);
    stopPlacing();
    setTerrainTool({ on: false });
    setHover(null);
  }, [upOn]);
  // 选中了别的东西(搜索、编年史):卡片让给它;改地形打开:收起
  useEffect(() => {
    if (selState.sel && getUpUi().on) closeUpheaval();
  }, [selState.sel]);
  useEffect(() => {
    if (terrainTool.on) closeUpheaval();
  }, [terrainTool.on]);
  // 编辑地形的「板块」页:地图换成板块配色(看得见边界和漂移箭头);离开这一页、收起编辑地形时换回原来的(其间作者自己换过就不动)
  const platePage = terrainTool.on && pageOf(terrainTool.tool) === 'plates';
  const beforePlates = useRef<{ base: BaseId; fill: FillId; sat: SatLook } | null>(null);
  useEffect(() => {
    if (platePage) {
      if (mapLayer !== 'plates') {
        // 记下整套底图 + 填色 + 卫星画法(旧的图层名合不下"高程底图上填国家"这类搭配)
        beforePlates.current = { ...mapViewRef.current };
        applyLayer('plates');
      }
    } else if (beforePlates.current) {
      if (mapLayer === 'plates') applyMapView(beforePlates.current);
      beforePlates.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 只在进出板块页时换
  }, [platePage]);

  // ---- 点选(阶段 4):单击(不是拖动)选中 城镇符号 / 城名 → 城,国名 → 国家,地名 → 地理实体;
  // 都没点到:"国家"开着时点到国土 → 国家,否则 → 州;点到海上 / 地图外 = 取消。双击(复位视图)不改选中 ----
  /** 双击的第一下之前选中的是什么(第二下时恢复) */
  const beforeClick = useRef<MapSelection | null>(null);
  const onStageClick = (e: React.MouseEvent) => {
    // 只管点在地图(或地图外的空白)上的:时间轴、按钮、图例上的点击冒泡上来不算
    const t = e.target as HTMLElement;
    if (t !== e.currentTarget && !t.closest('.canvas-wrap, .globe')) return;
    // 点地图收起菜单的那一下只收起菜单(dismissClick.ts)
    if (tookDismissClick()) return;
    // 地球仪还在备贴图:屏幕上还是平面图,点了不按看不见的球去选
    if (getGlobeOn() && !globeApi.current?.ready()) return;
    if ((getGlobeOn() ? globeApi.current?.dragged() : moved.current) || replayOn) return;
    // 导出回放视频时:地图只用来挪、缩放(框住要拍的地方),点了不选东西
    if (getFilm().mode) return;
    // 改地形:单击放火山 / 挖湖,不看详情(双击的第二下不再放)
    if (getTerrainTool().on) {
      if (e.detail < 2) terrainClick(worldAt(e.clientX, e.clientY));
      return;
    }
    // 地形大事:单击放火山,不看详情
    if (getUpUi().on) {
      if (e.detail < 2) upClick(worldAt(e.clientX, e.clientY));
      return;
    }
    // 新建时还没有历史,点了不看详情
    if (draft) return;
    // 作者的人物:正在填的时候点地图不选别的;挑地方时 = 选好那一处(城 / 州 / 海上那一点)
    const cu = getCharUi();
    if (civ && cu.draft) {
      if (e.detail >= 2 || !cu.picking) return;
      const w = whereAtClient(e.clientX, e.clientY);
      if (w) {
        pickPlace(w);
        setHover(null);
      }
      return;
    }
    // 作者标记:放标记 = 在点到的地方新建一个;正在填的标记:一个点 = 图钉挪到点到的地方,几个州 = 点到的州加进来 / 去掉(都不选别的)
    const mk = getMarkUi();
    if (civ && (mk.placing || mk.draft)) {
      if (e.detail >= 2 || performance.now() - pinDragEnd.current < 400) return;
      if (mk.draft?.scope === 'regions') {
        const r = regionAtClient(e.clientX, e.clientY);
        if (r >= 0) toggleDraftRegion(regionKey(civ, r));
        return;
      }
      const w0 = markWorldAt(e.clientX, e.clientY);
      if (!w0) return;
      // 点在关口符号(或关名)上:图钉吸到关口正中(钉在关上);拖图钉不吸,拖开就是普通的一个点
      const pass = passAt(e.clientX, e.clientY);
      const cell = pass >= 0 && civ.places[pass]?.kind === 'pass' ? civ.places[pass].cell : undefined;
      const w: [number, number] = cell !== undefined && data ? [data.world.mesh.x[cell], data.world.mesh.y[cell]] : w0;
      if (mk.placing) {
        newMarkDraft({ at: w, year: markYear() });
        setHover(null);
      } else patchDraft({ at: w });
      return;
    }
    // 双击的第二下(手指点两下时浏览器不一定数成 detail = 2):恢复第一下之前的选中
    if (e.detail >= 2 || performance.now() - dblTapAt.current < 600) {
      setSelection(beforeClick.current);
      return;
    }
    // 干预选对象国 / 迁都选城(阶段 4):点到的国家 / 城交给干预区,不改选中
    const pk = getPolityPick();
    if (pk) {
      const city = pk.target === 'settlement';
      const region = pk.target === 'region';
      const id = city ? settlementAtClick(e.clientX, e.clientY) : region ? regionAtClient(e.clientX, e.clientY) : polityAtClick(e.clientX, e.clientY);
      const err = id >= 0 ? pk.accept(id) : city ? '这里没有城,点一座城的符号或城名' : region ? '这里不是陆地,点一个州' : '这里没有国家,点一个国家的国土或国名';
      finishPick(pk, err);
      return;
    }
    beforeClick.current = getSelection().sel;
    const el = stageRef.current;
    const rect = el?.getBoundingClientRect();
    const side = rect && e.clientX - rect.left > rect.width * 0.55 ? 'left' : 'right';
    // 作者的人物的头像(画在最上面,先看它)
    const ch = characterPinAt(e.clientX, e.clientY);
    if (ch !== null) return setSelection({ kind: 'character', id: ch }, side);
    // 作者标记(画在地名上面,先看它):图钉、名字、名字牌 = 选中它;合并的圆 = 在那里放大
    const mh = markHitAt(e.clientX, e.clientY);
    if (mh) {
      if (mh.kind === 'cluster') return zoomToCluster(e.clientX, e.clientY);
      return setSelection({ kind: 'mark', id: mh.ids[0] }, side);
    }
    const hit = labelAt(e.clientX, e.clientY);
    if (hit) return setSelection(hit, side);
    const c = cellAt(e.clientX, e.clientY);
    const r = civ && c >= 0 && c < civ.regions.of.length ? civ.regions.of[c] : -1;
    if (!civ || r < 0) return clearSelection();
    // 信仰图层:点陆地 = 那里信的那个教(国名、城名照旧打开国家、城)
    if (getCivShow().faiths && civ.religion) {
      const y = Math.min(civ.endYear, Math.max(0, getCivTime().year ?? civ.endYear));
      const f = faithAt(civ, y)[r];
      if (f >= 0) return setSelection({ kind: 'faith', id: f }, side);
    }
    if (getCivShow().polities && civ.polities.length) {
      const y = Math.min(civ.endYear, Math.max(0, getCivTime().year ?? civ.endYear));
      const po = ownersAt(civ, y).polity[r];
      if (po >= 0) return setSelection({ kind: 'polity', id: po }, side);
    }
    setSelection({ kind: 'region', id: r }, side);
  };
  /** 点到的城镇符号 / 城名 / 国名 / 地名(主图:文字层;地球仪:球上的符号文字层) */
  const labelAt = (x: number, y: number) => (getGlobeOn() ? (globeApi.current?.labelAt(x, y) ?? null) : pickLabelAt(x, y));
  /** 单击处的国家(时间轴当前那一年;点到国名也算;没有 = −1) */
  const polityAtClick = (x: number, y: number): number => {
    if (!civ) return -1;
    const hit = labelAt(x, y);
    if (hit?.kind === 'polity') return hit.id;
    const c = cellAt(x, y);
    const r = c >= 0 && c < civ.regions.of.length ? civ.regions.of[c] : -1;
    if (r < 0) return -1;
    const yr = Math.min(civ.endYear, Math.max(0, getCivTime().year ?? civ.endYear));
    return ownersAt(civ, yr).polity[r];
  };

  // 打开改地形:单击不再看详情,已经打开的详情面板、"在地图上点一个国家"一起收起
  useEffect(() => {
    if (!terrainTool.on) return;
    clearSelection();
    setPolityPick(null);
    stopPlacing();
  }, [terrainTool.on]);
  // 作者标记:放标记时顶部一条提示(取消 = Esc);换了世界、回到我的世界、回放世界形成时放标记、正在填的一律作废。
  // 开始放标记时,"在地图上点一个国家"(干预选目标)收起,免得两件事抢同一下点击
  const markPlacing = useMarkUi().placing;
  useEffect(() => {
    if (markPlacing) setPolityPick(null);
  }, [markPlacing]);
  useEffect(() => {
    if (markPlacing) showToast({ id: 'mk', kind: 'info', text: '点地图放标记', more: ['陆地、海上都可以'], action: { label: coarse ? '取消' : '取消 · Esc', act: 'mark-cancel', onClick: stopPlacing } });
    else clearToast('mk');
  }, [markPlacing, coarse]);
  // 作者的人物:挑地方时顶部一条提示(取消 = Esc);开始挑时"在地图上点一个国家"收起
  const charPicking = useCharUi().picking;
  useEffect(() => {
    if (charPicking) {
      setPolityPick(null);
      showToast({
        id: 'oc-pick',
        kind: 'info',
        text: charPicking === 'birth' ? '点地图选出生地' : '点地图选这段经历在哪',
        more: ['城、州、海上都可以'],
        action: { label: coarse ? '取消' : '取消 · Esc', act: 'character-pick-cancel', onClick: stopPicking },
      });
    } else clearToast('oc-pick');
  }, [charPicking, coarse]);
  /** 能放标记:建好的世界、有历史(新建、回放世界形成时不行) */
  const markable = !!data && stage === 'world' && !!civ && !replayOn;
  const markWorld = data?.world;
  useEffect(() => {
    resetMarkUi();
    resetCharacterUi();
  }, [markWorld, home, replayOn, draft]);

  /** 单击处的城(点到城镇符号 / 城名;否则点到的州里时间轴当前那一年还在的城;没有 = −1) */
  const settlementAtClick = (x: number, y: number): number => {
    if (!civ) return -1;
    const hit = labelAt(x, y);
    if (hit?.kind === 'settlement') return hit.id;
    const c = cellAt(x, y);
    const r = c >= 0 && c < civ.regions.of.length ? civ.regions.of[c] : -1;
    if (r < 0) return -1;
    const yr = Math.min(civ.endYear, Math.max(0, getCivTime().year ?? civ.endYear));
    const s = civ.settlements.find((q) => q.region === r && q.founded <= yr && (q.ended === undefined || q.ended > yr));
    return s ? s.id : -1;
  };
  // 浏览器自己的页面缩放不抢捏合:
  // - 手机:双指捏合(Safari 的 gesture 事件;别的浏览器靠 touch-action,见 app.css),交给上面的手指处理
  // - 电脑上 Safari 的触控板捏合也是 gesture 事件(没有手指按在屏幕上):落在地图上就缩放地图
  // - Chrome、Firefox 的触控板捏合是按着 Ctrl 的滚轮:落在侧栏、时间轴、按钮上时也拦下,不放大整个网页
  useEffect(() => {
    /** 这次触控板捏合上一回的倍数(0 = 不归地图管) */
    let pinchAt = 0;
    const onMap = (t: EventTarget | null) => {
      const el = t as HTMLElement | null;
      return !!el?.closest?.('.stage') && !el.closest('.inspector');
    };
    const start = (e: Event) => {
      e.preventDefault();
      const fingers = touches.current.size > 0;
      setGesturePinch(!fingers);
      pinchAt = !fingers && onMap(e.target) ? 1 : 0;
    };
    const change = (e: Event) => {
      e.preventDefault();
      const g = e as Event & { scale?: number; clientX?: number; clientY?: number };
      if (!pinchAt || touches.current.size || !(typeof g.scale === 'number' && g.scale > 0)) return;
      const f = g.scale / pinchAt;
      pinchAt = g.scale;
      const el = stageRef.current;
      if (!el || !Number.isFinite(f)) return;
      const rect = el.getBoundingClientRect();
      const cx = g.clientX ?? mouseAt.current[0];
      const cy = g.clientY ?? mouseAt.current[1];
      touchRef.current();
      if (getGlobeOn()) globeApi.current?.zoomBy(f, cx, cy, true);
      else zoomRef.current(cx - rect.left, cy - rect.top, f);
    };
    const end = () => {
      pinchAt = 0;
      setGesturePinch(false);
    };
    const isPinch = createPinchGuard();
    const pageZoom = (e: WheelEvent) => {
      if (e.ctrlKey && isPinch(wheelSample(e))) e.preventDefault();
    };
    document.addEventListener('gesturestart', start, { passive: false });
    document.addEventListener('gesturechange', change, { passive: false });
    document.addEventListener('gestureend', end);
    window.addEventListener('wheel', pageZoom, { passive: false, capture: true });
    return () => {
      document.removeEventListener('gesturestart', start);
      document.removeEventListener('gesturechange', change);
      document.removeEventListener('gestureend', end);
      window.removeEventListener('wheel', pageZoom, { capture: true });
    };
  }, []);
  // Esc:先取消"在地图上点一个国家 / 城",再取消选中(在输入框里打字时不管)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (escapeCharacter()) return;
      if (getUpUi().on) return closeUpheaval();
      const mk = getMarkUi();
      if (mk.placing) return stopPlacing();
      if (mk.draft) return cancelDraft();
      if (getPolityPick()) return setPolityPick(null);
      clearSelection();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  // 键盘快捷键(按键对照见 shortcuts.ts;光标在输入框里、弹窗开着时不管,见 useShortcuts.ts)。返回 false = 这一下不归快捷键管
  useShortcuts((a) => {
    if (home || !data) return false;
    const end = civ?.endYear ?? 0;
    // 有历史可放:建好的世界、长出了文明、不在回放世界形成
    const history = !draft && !!civ && civ.viable && !replayOn;
    // 宽屏、建好的世界:左边的卡片能收起(sideStore.ts);收起着要用卡片里的搜索框、存档时先展开
    const foldable = !narrow && !!world && stage === 'world';
    const sideHidden = () => foldable && getSide().collapsed && !getSide().peek;
    const showSide = () => sideHidden() && flushSync(expandSide);
    switch (a) {
      case 'play':
        if (!history) return false;
        // 逐年推演:播放 / 暂停只管这一段(停着的时候 = 接着演绎)
        if (getStepwise().on) stepwiseToggle();
        else togglePlayback(end, replayStart(end));
        return true;
      case 'back':
      case 'forward':
      case 'back100':
      case 'forward100':
        if (!history) return false;
        if (getStepwise().on) stepwiseNudge((a === 'back' || a === 'back100' ? -1 : 1) * (a.endsWith('100') ? 100 : 10));
        else stepYear(end, (a === 'back' || a === 'back100' ? -1 : 1) * (a.endsWith('100') ? 100 : 10));
        return true;
      case 'jump':
        // 时间轴上的年份变成输入框(JumpYear.tsx);时间轴藏着、锁着时不管
        return history && openJump();
      case 'zoomIn':
      case 'zoomOut':
        zoomButton(a === 'zoomIn' ? 1.5 : 1 / 1.5);
        return true;
      case 'layer1':
      case 'layer2':
      case 'layer3':
      case 'layer4':
      case 'layer5': {
        const i = Number(a.slice(5)) - 1;
        if (draft) {
          const id = DRAFT_SEG[i];
          if (!id) return false;
          applyLayer(id);
          return true;
        }
        // 平常:1–4 = 填色(国家 / 民族 / 信仰 / 不填)
        const f = FILL_KEYS[i];
        if (!f || !data) return false;
        applyMapView({ fill: f });
        return true;
      }
      case 'search': {
        showSide();
        const box = [...document.querySelectorAll<HTMLInputElement>('input.search-input')].find(
          (el) => !el.disabled && el.getClientRects().length > 0 && !el.closest('[inert]'),
        );
        if (!box) return false;
        box.focus();
        box.select();
        return true;
      }
      case 'undo':
      case 'redo':
        // 改地形工具开着:它自己管(撤销一笔);新建世界时 ⌘Z 也是撤销一笔地形
        if (getTerrainTool().on) return false;
        // 地形大事的卡片开着:撤销这一件里的最后一笔
        if (getUpUi().on) {
          if (a === 'undo') undoUpOp();
          return true;
        }
        if (draft) {
          if (a === 'undo') undoTerrainOp();
          return true;
        }
        if (a === 'undo') undoLastEdit();
        else redoLastEdit();
        return true;
      case 'save':
        if (draft) return false;
        showSide();
        return openSaveMenu();
      case 'side':
        // 和卡片上的收起按钮、收起后左上角的小按钮一样(卡片弹出来显示选中的东西时 = 收回去)
        if (!foldable) return false;
        if (sideHidden()) expandSide();
        else collapseSide();
        return true;
      case 'help':
        openShortcuts();
        return true;
    }
  });

  /** 平面主图 ⇄ 地球仪:两边的中心经度接上(地球仪从主图当前的中心转起;切回主图时转到地球仪正对着的经度) */
  const toggleGlobe = () => {
    setHover(null);
    if (!getGlobeOn()) return setGlobeOn(true);
    // 切回上一个平面投影(中心接上地球仪正对着的经度,见上面换投影那一段)
    setGlobeOn(false);
  };
  // 地球仪:回放帧、地形画布什么时候重画过(换世界 / 画风 / 图层)
  const globeReplay = useMemo(
    () => (replayOn && replay ? { w: replay.w, h: replay.h, frame: replay.frames[replay.idx] } : null),
    [replayOn, replay],
  );
  const terrainKey = useMemo(() => ({ data, style, layer, look: terrainLook }), [data, style, layer, terrainLook]);
  const onGlobeHover = (p: [number, number] | null) => {
    if (!p || !data || replayOn) return setHover(null);
    const [x, y] = mouseAt.current;
    const mh = draft ? null : (charHoverAt(x, y) ?? markHoverAt(x, y));
    if (stageRef.current) stageRef.current.style.cursor = mh ? mh.cursor : '';
    if (mh && mh.info !== undefined) return markHoverCard(mh, x, y);
    showHover(p, globeApi.current?.labelAt(x, y) ?? null, x, y);
  };
  // ---- 顶部提示条:生成进度、重推历史、选目标、改地形的结果(同一时间只显示最近的一条) ----
  // 生成世界(首次打开、换种子、调参数、读档)/ 按新地形重新生成:一行"正在…",小字是种子和这一步在做什么
  useEffect(() => {
    // 照故事找世界打开一个结果:地图顶上那一条写着"正在打开",不另出提示条
    if (progress && !finderOn)
      showToast({
        id: 'progress',
        kind: 'progress',
        text: progress.regen ? '正在按新地形重新生成' : '正在生成世界',
        more: [progress.seed !== undefined && !progress.regen ? `种子 ${progress.seed}，${progress.stage}` : progress.stage],
        progress: progress.pct,
      });
    else clearToast('progress');
  }, [progress, finderOn]);
  // 回放世界形成:后台算各个年代的地形那一两秒(算好以后是地图上的字幕)
  const replayWait = replayOn && !replay;
  useEffect(() => {
    if (replayWait) showToast({ id: 'replay', kind: 'progress', text: '正在准备回放' });
    else clearToast('replay');
  }, [replayWait]);
  // 重推历史的进度、选目标的提示在 TargetPlates.tsx(和名牌、压暗一起)
  const terrainLast = terrainStatus.last;
  useEffect(() => {
    if (!terrainLast) return;
    // 对不上的改名先留着(撤销地形修改就会回来),没生效的干预概览里写了原因
    const lost = [
      terrainLast.lostNames ? `${terrainLast.lostNames} 处改名` : '',
      terrainLast.lostInterventions ? `${terrainLast.lostInterventions} 条干预` : '',
    ].filter(Boolean);
    const more = lost.length ? [`${lost.join('、')}暂未生效`] : undefined;
    const n = regenNote.current;
    regenNote.current = null;
    // 新建界面里助手执行、撤销以后不放提示条(撤销在助手那一行和左边「地形」里)
    if (n && getStage().stage === 'draft') return;
    if (n) {
      showToast({
        id: 'terrain',
        kind: lost.length ? 'warn' : 'ok',
        text: n.kind === 'apply' ? '已按你说的改写 · 按新地形重新生成' : '已撤销改写 · 按原来的地形重新生成',
        more,
        action:
          n.kind === 'apply' && n.undo
            ? {
                label: '撤销',
                act: 'rw-undo',
                onClick: () => {
                  n.undo?.();
                  clearToast('terrain');
                },
              }
            : undefined,
      });
      return;
    }
    const tip = holdTip.current;
    holdTip.current = false;
    // 补推历史、起地名已经开始了(还没换上就收起了编辑地形):不再说重新生成好了,看"正在起地名"
    if (naming.current) return;
    showToast({ id: 'terrain', kind: lost.length ? 'warn' : 'ok', text: '已按新地形重新生成', more: tip ? [...(more ?? []), '地名等点「完成」以后再起'] : more });
  }, [terrainLast]);
  // 编辑地形以后补推历史、起地名:顶上"正在起地名",进度条按上一次推历史用的时间估;起好收起
  const namingOn = namingPct !== null;
  useEffect(() => {
    if (!namingOn) return;
    const cells = genParams.current?.cells ?? 36000;
    const est = Math.max(200, civMsLast.current ?? 500 * Math.pow(Math.max(1, cells / 36000), 0.6));
    const t = setInterval(() => {
      const n = naming.current;
      if (n) setNamingPct(Math.min(0.95, (performance.now() - n.t0) / (est * 1.15)));
    }, 100);
    return () => clearInterval(t);
  }, [namingOn]);
  useEffect(() => {
    if (namingPct === null) return clearToast('names');
    clearToast('terrain');
    showToast({ id: 'names', kind: 'progress', text: '正在起地名', more: ['按新地形起山河湖海的名字'], progress: namingPct });
  }, [namingPct]);
  // 地名刚起好:地图上的字淡入(见 app.css 的 .screen-layer.names-in;星球上的等卷成星球、停稳才排,多留一会儿),淡完摘掉
  useEffect(() => {
    if (!namesIn) return;
    return cancelTimeout(setTimeout(() => setNamesIn(0), 1200));
  }, [namesIn]);

  // 推演出来没有文明(宜居的陆地太少):建好的世界说一句(新建时卡片上写,可以换一颗)
  const noCiv = !!rawCiv && !rawCiv.viable;
  const noCivToast = noCiv && stage === 'world';
  useEffect(() => {
    if (!noCivToast) return clearToast('world');
    showToast({ id: 'world', kind: 'warn', text: '这个世界没有文明', more: ['宜居的陆地太少'] });
  }, [noCivToast]);

  const civReady = !!civ && civ.viable;
  /** 正在重推 / 按新地形重新生成 / 生成新世界:助手这时发不了话、确认单也不能执行 */
  const worldBusy = !!resim || terrainStatus.busy || !!progress || namingPct !== null;
  // 助手:换了世界、世界建好了,对话跟着换;离开建好的世界(回我的世界、新建)不再看试推演。
  // 打开另一个参数、地形、名字都一样的存档时历史原样复用,所以还要跟着世界的 id(存档一变 App 就重新渲染)
  const worldId = currentWorld()?.id ?? null;
  useEffect(() => syncAssistantWorld(draft ? 'history' : 'terrain'), [rawCiv, draft, data, worldId]);
  useEffect(() => {
    if (stage !== 'world') exitPreview();
  }, [stage]);
  // 在地图上看试推演:面板里是试推演的历史,只许改两份历史里是同一个的国家、城(改名、下令用它的键)
  useEffect(() => {
    const real = rawCiv;
    const sim = previewRaw;
    if (!real || !sim) return;
    setEditGate((keys) => (keys.every((k) => sameInBoth(real, sim, k)) ? null : PREVIEW_EDIT_BLOCK));
    return () => setEditGate(null);
  }, [rawCiv, previewRaw]);
  // 逐年推演切支线的时候:面板里还是原来那支的历史,先不许下令、改名(逐年推演里不试推演,和上面那个不会同时挂着)
  useEffect(() => {
    let on = false;
    const sync = () => {
      const want = !!getStepwise().switching;
      if (want === on) return;
      on = want;
      setEditGate(want ? () => SWITCH_EDIT_BLOCK : null);
    };
    sync();
    const off = subscribeStepwise(sync);
    return () => {
      off();
      if (on) setEditGate(null);
    };
  }, []);
  // 在地图上看试推演 / 回到现在:选中的东西按稳定键换到另一份历史里;刚开始看时没选东西,选上关注的那个国家
  const prevPreview = useRef<Civ | null>(null);
  useLayoutEffect(() => {
    const was = prevPreview.current;
    prevPreview.current = previewRaw;
    const real = rawRef.current;
    const from = was ?? real;
    const to = previewRaw ?? real;
    if (was === previewRaw || !from || !to || from === to) return;
    remapSelection(from, to);
    if (!previewRaw || was || getSelection().sel || !real) return;
    const p = getAssistant().preview;
    const v = p ? getAssistant().turns.find((t) => t.id === p.turn)?.proposal?.trial : undefined;
    const id = v && v.focus > 0 ? v.rows[0].id : -1;
    if (id < 0 || !real.polities[id]) return;
    const r = resolveKey(previewRaw, polityKey(real, id));
    if (r && r.kind === 'polity') setSelection({ kind: 'polity', id: r.id });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [previewRaw]);
  // 详情面板只挂一份:挂进一个自己建的容器,窄屏把容器放在底部卡片的位置,宽屏放进侧栏(放哪儿由那边的空位 ref 决定)。
  // 窗口跨过窄屏断点(比如手机横过来)时面板不重新挂,正在干预的那几步、填了一半的年份和名字都留着
  const inspectorHost = useMemo(() => {
    const el = document.createElement('div');
    el.className = 'inspector-host';
    return el;
  }, []);
  const inspectorSlot = useCallback(
    (slot: HTMLElement | null) => {
      if (slot && inspectorHost.parentNode !== slot) slot.appendChild(inspectorHost);
    },
    [inspectorHost],
  );
  /** 建好的世界(不是新建中、不在我的世界):时间轴、详情、概览、事件标签这些才有 */
  const world = stage === 'world';
  const filmOn = !!filmUi.mode && !!data && world && !draft && !home;
  /** 导播停用:还没有历史、新建、回放世界形成、导出视频 / 长图时(这时时间轴照平常放) */
  const directorOff = !markable || filmOn || !civ?.viable || !civ.cultures.length;
  // 接着回放世界形成放文明时导播不管(事件小卡照旧)
  const directing = directorOnPref && !directorOff && !civStory;
  // 逐年推演(Stepwise.tsx):打开的世界在逐年推演(修改里有进度)。导播换成逐年推演那一份开关(默认开);
  // 时间轴只放这一段,时间轴上面换成单子 / 这一段的大事;停一下时手机上拉起卡片
  const stepWorld = world && !draft && !!cleanPlay(edits.play);
  const stepWas = useRef(stepWorld);
  /** 按在地图上的手指 / 鼠标(都松开了逐年推演接着走;松开的地方不一定在地图上,在整个页面上听) */
  const stepPointers = useRef(new Set<number>());
  useEffect(() => {
    const up = (e: PointerEvent) => {
      stepPointers.current.delete(e.pointerId);
      if (!stepPointers.current.size) setStepGesture(false);
    };
    window.addEventListener('pointerup', up, true);
    window.addEventListener('pointercancel', up, true);
    return () => {
      window.removeEventListener('pointerup', up, true);
      window.removeEventListener('pointercancel', up, true);
    };
  }, []);
  useEffect(() => {
    setDirectorMode(stepWorld);
    if (!stepWorld) leaveStepwise();
    // 进出逐年推演(开始演绎、存回推演模式打开了那一个):干预页、选目标是另一种样子,选中的东西收起
    if (stepWas.current !== stepWorld) {
      setPolityPick(null);
      clearSelection();
    }
    stepWas.current = stepWorld;
  }, [stepWorld]);
  const stepOn = useStepwiseOn() && stepWorld;
  const stepStopped = useStepwiseStopped() && stepOn;
  // 停一下的卡片、编号点:停着、没在往回看 / 重放(手机上卡片没收起);往回看、刚重新演绎停着时时间轴上面那一条占着字幕条的地方
  const stepCard = useStepCard() && stepOn;
  const stepStrip = useStepStrip() && stepOn;
  const stepReplay = useStepReplay();
  const stepQuiet = (stepStopped && !stepReplay) || stepStrip;
  /** 时间轴上有「再推」:推演模式里有文明时(逐年推演、导出视频、回放世界形成、新建时没有;藏起来时弹层跟着收起) */
  const extendShown = !!(data && world && !draft && !home && !stepOn && !replayOn && !filmOn && !previewRaw && civ?.viable && civ.cultures.length);
  useEffect(() => {
    if (!extendShown) setExtendOpen(false);
  }, [extendShown]);
  const curWorld = currentWorld();
  // 离开这个世界(回首页、去新建、浏览器前进后退换了一个世界),或者助手"先看看"的历史进来、退出(预览条上的"回到现在"):
  // 导出面板关掉,正在导出的视频取消(不然会接着拍已经不在屏幕上的那一份历史)
  const filmWorld = world && !draft && !home ? (curWorld?.id ?? '') : null;
  useEffect(() => {
    if (getFilm().mode) closeFilm();
  }, [filmWorld, previewRaw]);
  /** 打开别人分享的世界、还没改过:地图下那条说明代替第一次打开的操作提示 */
  const sharedOn = world && !!data && !!sharedFor && curWorld?.id === sharedFor.id && curWorld.kind === 'visit' && !terrainTool.on;
  /** 从作品墙打开的世界作品:地图左上那一条(改了自动另存以后也还在;回作品墙、换了世界就不放),侧栏左上的返回换成「‹ 作品墙」 */
  const workOn = world && !draft && !!workFor && curWorld?.id === workFor.id && !filmOn;
  const workBar = workOn && workFor && <WorkBar phone={narrow} work={workFor.work} onSaveCopy={keepWork} onNewCiv={() => newCivOnWork(workFor.work)} />;
  // 停在那一刻的说法:"第 1500 年，有桑皇朝"(国名、州名按那一年的;设了纪年的按纪年)
  const sharedAt = (() => {
    const a = sharedFor?.at;
    if (!a || !civ) return null;
    const sel = a.sel;
    const p = sel?.kind === 'polity' ? civ.polities[sel.id] : null;
    const name = p ? polityName(p, shownYearOf(p, a.year, civ.endYear)) : sel?.kind === 'region' && sel.id < civ.regions.count ? regionLabel(civ, sel.id) : null;
    return `${yearFull(a.year, edits.era)}${name ? `，${name}` : ''}`;
  })();
  /** 「从头放」:不停在这一刻了,和不带这一刻的链接打开时一样 —— 不选中、地图回到整张,从结束前一段起自动播放 */
  const replayShared = () => {
    setSharedFor((s) => (s ? { ...s, at: null } : s));
    clearSelection();
    if (getGlobeOn()) globeApi.current?.reset();
    else flyRef.current('home');
    if (civ) startAutoplay(replayStart(civ.endYear));
  };
  const layerProps = {
    base: mapBase,
    fill: mapFill,
    sat: satLook,
    civ,
    onBase: pickBase,
    onFill: (fill: FillId) => applyMapView({ fill }),
    onSat: (sat: SatLook) => pickBase('satellite', sat),
    pending: pendingBase,
    thumbs,
    requestThumbs,
    disabled: !data,
  };
  /** 新建界面确认创建:建好了就让平常的地图从星球展开时正中的经线接着看(放回 1 倍) */
  const studioCreate = (title: string, lon: number, how?: 'step' | 'outline'): boolean => {
    // 先立刻标上"新建界面正在退场"再清掉草稿:不然新建界面会被拆掉又重装一次,重装时照手绘图的笔又被打开
    flushSync(() => setStudioOut(1));
    const f = foundNow;
    if (!createWorld(title, how, how === 'step' ? undefined : f?.year)) {
      setStudioOut(0);
      return false;
    }
    if (f && how !== 'step') foundCreated(f);
    // 选了「演绎」:不停在开场那年、不加标记,大纲照样搬过去
    else if (f && how === 'step') moveFoundOutline(f);
    stopFly();
    publishMapCenter(wrapLon(lon));
    const el = stageRef.current;
    const g = geo.current;
    if (getProjection() === 'equirect' && el && g.bw && g.wrap) {
      const b = { sw: el.clientWidth, sh: el.clientHeight, bw: g.bw, bh: g.bh, padB: g.padB };
      const v0 = viewCentredAt({ k: 1, x: 0, y: 0 }, b, g.wrap, xOfLon(lon, g.wrap));
      const v = { ...v0, x: Math.round(v0.x) };
      viewRef.current = v;
      setView(v);
    }
    return true;
  };
  // 新建界面的「实景」是卫星(用记着的画法)
  const satThumb = baseThumb('satellite', satLook);
  const studioThumbs = { ...thumbs, realistic: thumbs[satThumb] };
  const studioRequest = (ids: MapLayer[]) => requestThumbs(ids.map((id): ThumbId => (id === 'realistic' ? satThumb : id)));
  const studioBase = (key: string) => baseCanvas(key === 'realistic' ? baseKeyOf('realistic', layer, satLook) : key);
  // 在一张地图上打造文明:用的是哪个世界的地图(它的名字;只存了地图的、那个世界已经删掉了 = null)
  // (看要打开的那一个:还在生成时套着的修改还是上一个世界的)
  const draftMap = draft ? targetRef.current?.edits.map : undefined;
  const draftMapFrom = useMemo(() => {
    if (!draftMap) return undefined;
    const w = draftMap.from ? loadWorld(draftMap.from) : null;
    const t = targetRef.current!;
    return { title: (w && !w.map && w.save.title) || null, brief: `种子 ${t.params.seed}，${mapBriefOf(t.params, t.edits)}` };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftMap, v]);
  const studio = ((draft && !finderOn) || studioOut > 0) && (
    <Studio
      onFinder={() => openFinderPage()}
      found={foundNow}
      onFoundBack={() => openFinderPage(true)}
      phone={narrow}
      mode={draftModeOf(targetRef.current)}
      params={params}
      title={draftTitle}
      base={stageBase}
      back={draftBack}
      onSeed={draftSeed}
      onRandomSeed={() => draftSeed(randomSeedValue())}
      onParams={draftParams}
      onTitle={draftRename}
      onCreate={studioCreate}
      onSaveMap={saveMap}
      mapFrom={draftMapFrom}
      // 以它为底稿新建、调过参数:带过来的干预要等重推完(不然创建时截的缩略图、放的历史是没干预的)
      busy={!!progress || !!resim}
      naming={namingPct !== null}
      later={namesHeld || namingPct !== null}
      namesIn={!!namesIn}
      onLeaveTerrain={releaseNames}
      ready={!!data && !progress}
      mapReady={!!data && (!progress || mapEarly)}
      noCiv={noCiv}
      data={data}
      baseWorld={baseData?.world ?? null}
      civ={realCiv}
      raw={rawCiv}
      worldBusy={worldBusy}
      layer={mapLayer}
      onLayer={applyLayer}
      baseCanvas={studioBase}
      thumbs={studioThumbs}
      requestThumbs={studioRequest}
      onFade={() => setStudioOut(2)}
      onGone={() => setStudioOut(0)}
    />
  );
  // 摊平改地形时舞台摆在新建界面中间那块
  const fr = studioOn ? studioFlat?.rect : undefined;
  // 经纬网的度数写在哪(地球仪、回放、导出预览、首页时不写;新建世界只在摊平改地形时写)
  const gratSpec: GratSpec | null = (() => {
    if (!graticule || globeOn || home || filmOn || (replayOn && replay)) return null;
    const fs = narrow ? 10 : 11;
    if (fr) {
      if (curved) return null;
      // 框外的字不出窗口
      const outX: [number, number] = [-fr.x, window.innerWidth - fr.x];
      if (narrow) return { fs, outX, lon: [{ side: 'bottom', out: true }], lat: [{ side: 'left', out: false }] };
      // 照手绘图新建:框上边紧挨切换条,经度只写下边
      const top = draftModeOf(targetRef.current) === 'image' ? [] : [{ side: 'top' as const, out: true }];
      return { fs, outX, lon: [...top, { side: 'bottom', out: true }], lat: [{ side: 'left', out: true }, { side: 'right', out: true }] };
    }
    if (studioOn) return null;
    const [, top, right, bottom] = freeArea(sb, panelOpen);
    // 电脑:纬度贴着侧栏卡片右边写(卡片收起了贴着屏幕左边),经度让开右下角那一列按钮
    const left = narrow ? 0 : Math.max(0, sideRoom(sb.sw) - 14);
    return { fs, area: [left, top, right, bottom], lonInRight: narrow ? undefined : right - 96, lon: [{ side: 'bottom', out: false }], lat: [{ side: 'left', out: false }] };
  })();
  const stagePos: CSSProperties | undefined = fr && { left: fr.x, top: fr.y, width: fr.w, height: fr.h, right: 'auto', bottom: 'auto' };
  // 两层放大的地图框共用一个变换、按视窗裁;两层屏幕层按同一个视窗裁(见下面的 JSX)
  const wrapStyle: CSSProperties = { transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})`, clipPath: wrapClip(view, sb, wrapW), display: globeOn && globeShown ? 'none' : undefined };
  const screenStyle: CSSProperties = { clipPath: screenClip(view, sb, wrapW), display: globeOn && globeShown ? 'none' : undefined };
  // 装着地图各层的容器:换了世界、历史就换个记号,免得容器记着的旧 props 拉住旧世界(见 holdMark.ts)
  const hold = holdMark(data, civ, shownRaw);
  return (
    <div
      className={`app${narrow ? ' phone' : ' has-side'}${chron.open ? ' chron-open' : ''}${panelOpen ? ' panel-open' : ''}${narrow && panelOpen && panelUi.sheet === 'full' ? ' sheet-full' : ''}${narrow && !selState.sel && !upOn && !filmOn && panelUi.world === 'full' ? ' world-full' : ''}${narrow && panelUi.drag ? ' sheet-drag' : ''}${narrow && selState.sel && !panelOpen ? ' sheet-away' : ''}${!narrow && world && sideUi.collapsed && !sideUi.peek ? ' side-collapsed' : ''}${picking ? ' picking' : ''}${globeOn ? ' globe-on' : ''}${data ? '' : ' booting'}${home ? ' home' : ''}${draft ? ' draft' : ''}${studioOn ? ' studio-on' : ''}${fr ? ' studio-flat' : ''}${astOpen && !narrow && !home && !draft ? ' ast-open' : ''}${preview ? ' ast-preview' : ''}${filmOn ? ' film-on' : ''}${filmOn && filmUi.mode === 'long' ? ' film-long' : ''}${stepOn ? ' step-on' : ''}${stepCard && !selState.sel ? ' step-stop' : ''}`}
      data-theme={theme}
      data-layer={mapLayer}
      data-base={mapBase}
      data-fill={mapFill}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {/* 地图铺满全屏(地形画布是页面上第一张 canvas:画面回归检查、截图脚本按它取图) */}
      <main
        ref={stageRef}
        className={`stage${terrainTool.on ? ' terrain-on' : ''}${upOn ? ' up-on' : ''}`}
        style={stagePos}
        onPointerDown={onPointerDown}
        onPointerDownCapture={(e) => {
          // 导播放着:一按地图(拖、点、捏合;地球仪上也算)镜头就交还,导播停在这件事上等着
          directorHandBack();
          // 逐年推演:按着地图的时候世界先不往下走(手指、鼠标都松开了接着走)。导播开着时上面那句已经停下了,
          // 和推演模式一样等用的人点「回到导播」或播放键
          stepPointers.current.add(e.pointerId);
          setStepGesture(true);
          onTouchDownCapture(e);
          onMarkDownCapture(e);
        }}
        onWheelCapture={() => {
          directorHandBack();
          stepWheel();
        }}
        onPointerMove={onPointerMove}
        onPointerMoveCapture={(e) => {
          mouseAt.current = [e.clientX, e.clientY];
          onTouchMoveCapture(e);
          onMarkMoveCapture(e);
        }}
        onPointerUp={onPointerUp}
        onPointerUpCapture={(e) => {
          onTouchUpCapture(e);
          onMarkUpCapture(e);
        }}
        onPointerCancel={onPointerUp}
        onPointerCancelCapture={(e) => {
          onTouchUpCapture(e);
          onMarkUpCapture(e);
        }}
        onClick={onStageClick}
        onPointerLeave={() => {
          setHover(null);
          terrainMove(null);
          upMove(null);
        }}
        onDoubleClick={resetView}
      >
        {/* 地图分四层叠(见 mapWrap.ts 的"屏幕层"):和世界一样大的画布放在被 CSS 放大的地图框里,
            按屏幕像素画的(细节层、视窗装饰、文字层)放在不缩放的屏幕层里 */}
        <div className="canvas-wrap" style={wrapStyle}>
          <div className="map-box" data-wrap={curved ? undefined : '1'} data-proj={projection} style={{ width: box.w, height: box.h }}>
            <canvas ref={canvasRef} />
            {/* 右边接的那一份(左右无限拖动,见 mapWrap.ts;弯边投影时不用) */}
            <canvas ref={canvasCopyRef} className="wrap-copy" />
          </div>
        </div>
        <div className="screen-layer" data-hold={hold} style={screenStyle}>
          {/* 放大后的地形细节(弯边投影:按投影一行一行铺) */}
          {data && <TerrainDetail world={data.world} raster={data.raster} style={style} look={terrainLook} view={view} mp={mp} />}
          {data && contourOn && <ContourLayer world={data.world} raster={data.raster} kind={contourKind!} style={contourStyle} dark={baseDark(mapBase)} view={view} mp={mp} />}
          {data && <MapDecor world={data.world} style={style} ink={contourStyle} view={view} mp={mp} />}
        </div>
        {/* 放大后的文明细节层(CivLayer 放进来):盖住下面的地形,在文明底图那一层地图框之下 */}
        <div className={`screen-layer${namesIn ? ' names-in' : ''}`} ref={setCivDetailHost} style={screenStyle} />
        <div className="canvas-wrap-upper" data-hold={hold} style={wrapStyle}>
          <div className="map-box-upper" data-hold={hold} style={{ width: box.w, height: box.h }}>
            {data && (
              <CivLayer world={data.world} raster={data.raster} civ={namesHeld ? null : civ} geo={namesHeld ? null : shownRaw} style={style} view={view} mp={mp} labelsHost={labelsHost} detailHost={civDetailHost} flags={flagView} />
            )}
            <canvas ref={overlayRef} className={`overlay ${replayOn && replay ? 'show' : ''}`} />
            <canvas ref={overlayCopyRef} className={`overlay wrap-copy ${replayOn && replay ? 'show' : ''}`} />
            {/* 照手绘图新建:原图 / 认出来的 / 叠上原图(在改地形覆盖层底下,笔画在它上面) */}
            {data && !curved && draft && <SourceLayer width={data.world.width} height={data.world.height} wrap={wrapW} />}
            {data && !curved && (
              <TerrainOverlay width={data.world.width} height={data.world.height} shown={shownTerrain} shownSketch={shownSketch} wrap={wrapW} scale={(box.w / data.world.width) * view.k} />
            )}
          </div>
        </div>
        {/* 文字层(CivLayer 放进来);回放世界形成时、认图时、照手绘图新建看原图或认出来的时藏起来(回放画面盖住文明层,字也不露出来;认图时只看图) */}
        <div className={`screen-layer${namesIn ? ' names-in' : ''}`} ref={setLabelsHost} style={(replayOn && replay) || importing || (draft && sourceView.show !== 'grown') ? { ...screenStyle, display: 'none' } : screenStyle} />
        {/* 地形大事:涂的地方、会变的地块、会没了的城盖在地名上面(和地图一起缩放) */}
        {data && !curved && upOn && (
          <div className="canvas-wrap-upper" data-hold={hold} style={wrapStyle}>
            <div className="map-box-upper" data-hold={hold} style={{ width: box.w, height: box.h }}>
              <UpheavalOverlay civ={civ} world={data.world} wrap={wrapW} scale={(box.w / data.world.width) * view.k} />
            </div>
          </div>
        )}
        {/* 地图上钉在事发地的事件标签;导播开着时播放经过的大事换成导播的圆环 + 名牌(Director.tsx),点编年史跳过去的照旧 */}
        {data && world && <EventPins civ={civ} world={data.world} toClient={globeOn ? globeToClient : worldToClient} hidden={replayOn || filmOn} quiet={directing} />}
        {/* 照故事找世界:选中的那个世界上故事里各国、隘口、交界的小牌子 */}
        {finderOn && <FinderPins ui={finder} phone={narrow} preview={finderPreviewData} toClient={globeOn ? globeToClient : worldToClient} />}
        {data && world && <DirectorPin toClient={globeOn ? globeToClient : worldToClient} hidden={directorOff || stepQuiet} />}
        {/* 逐年推演停一下:地图上按先后标出这一段的大事 */}
        {data && world && stepCard && <StepPins toClient={globeOn ? globeToClient : worldToClient} phone={narrow} />}
        {data && globeOn && (
          <Globe
            world={data.world}
            raster={data.raster}
            civ={civ}
            geo={shownRaw}
            style={style}
            layer={layer}
            look={terrainLook}
            terrain={canvasRef.current}
            terrainKey={terrainKey}
            replay={globeReplay}
            startLon={getMapCenter()}
            apiRef={globeApi}
            onHover={onGlobeHover}
            onOpened={() => setGlobeShown(true)}
            leftRoom={sideRoom(stageSize.w)}
            rightRoom={astOpen ? astRoom(stageSize.w) : 0}
          />
        )}
        {/* 作者标记(图钉、圈的州;地球仪上也画):在地名、地球仪上面 */}
        {data && world && <MarkLayer civ={civ} world={data.world} api={markApi} hidden={replayOn || draft || home} style={style} />}
        {/* 作者的人物一生的足迹(选中一个人物时;地球仪上也画):在标记上面 */}
        {data && world && <CharacterLayer civ={civ} world={data.world} raster={data.raster} api={markApi} hidden={replayOn || draft || home} />}
      </main>
      {/* 经纬网的度数:新建世界摊平改地形时写在框外,平常的世界页写在地图里贴着左边、下边(GratLabels.tsx) */}
      {data && gratSpec && (
        <GratLabels W={data.world.width} H={data.world.height} view={view} sb={sb} mp={mp} step={graticule} spec={gratSpec} ink={contourStyle} pos={fr} />
      )}
      {/* 导出回放视频:地图压暗、中间的预览,或者地图上的框(FilmStage.tsx) */}
      {filmOn && filmUi.mode === 'video' && <FilmStage phone={narrow} style={style} layer={layer} look={terrainLook} />}
      {/* 故事长图:地图压暗、中间的长图预览和右边一条全貌(手机整屏是预览;LongStage.tsx) */}
      {filmOn && filmUi.mode === 'long' && <LongStage phone={narrow} style={style} layer={layer} look={terrainLook} />}
      {/* 选干预目标 / 推演中:压暗地图、浮出名牌;选中国家:国都的圆环(TargetPlates.tsx) */}
      {data && world && <TargetLayer civ={civ} world={data.world} toClient={globeOn ? globeToClient : worldToClient} resim={resim} generating={!!progress} labelAt={labelAt} />}

      {replayOn && replay && !home && (
        <div className="caption">
          <div className="big">{replay.idx === replay.frames.length - 1 ? '今天' : `约 ${replay.mya[replay.idx]} 百万年前`}</div>
          <div className="small">板块碰撞抬起山脉,河流一点点把它切开</div>
          <div className="track">
            <div style={{ width: `${((replay.idx + 1) / replay.frames.length) * 100}%` }} />
          </div>
        </div>
      )}

      {home ? (
        /* 我的世界:盖住整个页面(地图留在底下,回到刚才的世界不用重新生成) */
        landing ? (
          <ShareGone
            phone={narrow}
            state={landing}
            onHome={() => {
              setLanding(null);
              goHome();
            }}
            onNew={() => {
              setLanding(null);
              startDraft();
            }}
          />
        ) : wall?.kind === 'list' ? (
          <GalleryPage
            phone={narrow}
            onHome={goHome}
            onOpen={(w) => openWork(w.id)}
            onPreset={takePresetWork}
            preset={wall.preset}
            onPresetShown={(id) => {
              // 开着的新建参数作品写进网址(刷新、复制网址还是它);不算一步
              navReplace({ page: 'gallery', ...(id ? { id } : {}) });
              writeGalleryUrl(id ?? '');
            }}
          />
        ) : wall?.kind === 'map' ? (
          <MapWorkView phone={narrow} work={wall.work} onBack={showGallery} onNewCiv={() => newCivOnWork(wall.work)} />
        ) : wall?.kind === 'work' ? (
          <WorkGone phone={narrow} state={wall.state} onHome={goHome} onGallery={showGallery} onRetry={() => openWork(wall.id)} />
        ) : (
          <MyWorlds phone={narrow} onOpen={openStored} onNew={startDraft} onOpenText={openText} onNewCiv={startNewCiv} onGallery={showGallery} onOpenWork={(w) => openWork(w.id)} />
        )
      ) : narrow ? (
        <>
          {/* 手机:底部的世界卡片(没选东西时;选中了东西换成详情卡片)、右上竖排的毛玻璃按钮(图层、地球);数据图层的图例、旧网站的「旧版」(测试网站的「测试版」)标记在左上。
              界面都在卡片和毛玻璃按钮上,地图上不再压字、不用渐变遮罩;最近大事在世界卡片拉到顶时的列表里。
              新建时这些都不放(新建界面自己一套) */}
          {filmOn ? (
            filmUi.mode === 'long' ? <LongPanel phone style={style} baseName={baseName(mapBase, satLook)} /> : <FilmPanel phone style={style} layer={layer} look={terrainLook} />
          ) : !draft && !selState.sel && !upOn && (
              <PhoneSheet
                data={data}
                civ={civ}
                raw={shownRaw}
                params={params}
                generating={!!progress}
                replay={{ on: replayOn, ready: !!replay }}
                onReplay={startReplay}
                onHome={workOn ? showGallery : goHome}
                homeLabel={workOn ? '作品墙' : undefined}
                exp={{ data, civ, plain: plainCiv, style, layer, look: terrainLook }}
              />
          )}
          {!draft && !filmOn && <PhoneButtons layers={layerProps} globeOn={globeOn} onToggleGlobe={toggleGlobe} marking={markable ? markPlacing : undefined} director={!directorOff} />}
          {!draft && (OLD_SITE !== null || BETA_SITE || style === 'data' || atlasOn || contourOn || workOn) && (
            <div className="corner-tl">
              {workBar}
              <OldSiteBadge />
              {(style === 'data' || atlasOn || contourOn) && <Legend layer={style === 'data' ? layer : atlasOn ? 'atlas' : null} contours={contourOn ? contourKind : null} ink={contourInkNow} zoom={view.k} phone />}
            </div>
          )}
        </>
      ) : (
        <>
          {/* 宽屏:左边侧栏(世界 / 选中的东西的详情、搜索、存档);右上图层、导出、编年史;数据图层的图例、旧网站的「旧版」(测试网站的「测试版」)标记在地图左上。新建时都不放(新建界面自己一套) */}
          {filmOn ? (
            filmUi.mode === 'long' ? <LongPanel phone={false} style={style} baseName={baseName(mapBase, satLook)} /> : <FilmPanel phone={false} style={style} layer={layer} look={terrainLook} />
          ) : !draft && (
            <Sidebar
              data={data}
              civ={civ}
              raw={shownRaw}
              params={params}
              generating={!!progress}
              replay={{ on: replayOn, ready: !!replay }}
              onReplay={startReplay}
              onHome={workOn ? showGallery : goHome}
              homeLabel={workOn ? '作品墙' : undefined}
              inspectorSlot={inspectorSlot}
            />
          )}
          {!draft && <MapBar civ={civ} layers={layerProps} exp={{ data, civ, plain: plainCiv, style, layer, look: terrainLook }} />}
          {!draft && (OLD_SITE !== null || BETA_SITE || workOn || ((style === 'data' || atlasOn || contourOn) && !terrainTool.on)) && (
            <div className="corner-tl">
              {workBar}
              <OldSiteBadge />
              {(style === 'data' || atlasOn || contourOn) && !terrainTool.on && <Legend layer={style === 'data' ? layer : atlasOn ? 'atlas' : null} contours={contourOn ? contourKind : null} ink={contourInkNow} zoom={view.k} />}
            </div>
          )}
        </>
      )}
      {/* 新建世界:和平常页面分开的一套深色界面,盖在地图上面(创建以后展开成平常的地图、淡出) */}
      {studio}
      {/* 照故事找世界:新建界面收起,左边找世界的卡片(手机:整页 / 底部卡片),地图上顶上一条、条件页淡着 */}
      {finderOn && (
        <>
          <FinderOverlay ui={finder} phone={narrow} preview={finderPreviewData} loading={!!progress} onUse={takeFinderPick} />
          <FinderPage
            phone={narrow}
            seed={finderBack.current?.target.params.seed ?? params.seed}
            preview={finderPreviewData}
            onExit={exitFinder}
            back={outlineSrc ? '大纲' : undefined}
            onUse={takeFinderPick}
            onFly={finderFly}
          />
        </>
      )}
      {/* 助手面板(宽屏右边一张卡片,手机是拉到顶的底部卡片;窗口跨过窄屏断点时不重新挂,没发出去的话留着)、在地图上看试推演时的提示条 */}
      {astOpen && aiOn && !home && !studioOn && data && realCiv && rawCiv && (
        <AssistantPanel phone={narrow} world={data.world} raster={data.raster} civ={realCiv} raw={rawCiv} lock={draft ? 'history' : 'terrain'} busy={worldBusy} />
      )}
      {world && <PreviewBanner busy={worldBusy} phone={narrow} />}
      {/* 顶部居中:提示条(同一时间只有一条) */}
      <ToastBar />
      {/* 「照大纲推演」先问多认真地试 */}
      <OutlineRunAsk />
      {/* 逐年推演里演一国:顶上常驻的方针条(提示条出来时让开) */}
      {data && world && civ && <RoleBar civ={civ} phone={narrow} />}
      {/* 右下(时间轴上方):地球 / 平面、放大、缩小。触屏不放 + −(用双指捏合);窄屏整个不放(地球在右上竖排的按钮里) */}
      <MapControls
        globeOn={globeOn}
        onToggleGlobe={toggleGlobe}
        onZoom={zoomButton}
        shifted={false}
        hidden={!data || narrow || home || draft}
        zoom={!coarse}
        marking={markable ? markPlacing : undefined}
        director={!directorOff}
      />
      {sharedOn ? (
        <SharedHint phone={narrow} short={sharedFor.short} by={sharedFor.by} own={sharedFor.own} at={sharedAt} onReplay={replayShared} onOk={() => setSharedFor(null)} />
      ) : (
        <FirstHint show={hintOn && !!data && world && !terrainTool.on && !upOn} touch={coarse} />
      )}
      {world && !narrow && <UpheavalHint />}
      {/* 底部:时间轴(宽屏是卡片右边那一块底下的胶囊;手机是浮在底部卡片上面的胶囊);新建时还没有历史,不放 */}
      <div className="bottom-row">
        <div className="bottom-tl">
          {data && world && (stepOn ? <StepTimeline civ={civ} phone={narrow} hidden={replayOn} /> : <CivTimeline civ={civ} hidden={replayOn} dock="inline" directorOff={directorOff} extendOff={!extendShown} />)}
        </div>
        {/* 待推演的单子:浮在时间轴上面(逐年推演里换成「下一步生效的干预」、停着的提示、这一段的大事) */}
        {data && world && !stepOn && <PendingTray phone={narrow} hidden={replayOn || draft} />}
        {data && world && stepOn && <StepDock phone={narrow} />}
        {/* 导播的字幕条:浮在时间轴上面 */}
        {data && world && <DirectorCaption phone={narrow} civ={civ} hidden={directorOff || stepQuiet} />}
        {/* 再推 N 年:电脑是「再推」上面的弹层,手机推的时候胶囊上面一张小卡片 */}
        {data && world && civ && !narrow && <ExtendPop end={civ.endYear} hidden={!extendShown} />}
        {data && world && narrow && <ExtendDock hidden={!extendShown} />}
      </div>
      {/* 导播:推进时间轴(不画东西;逐年推演时由 StepwiseEngine 推)、右上「导播略过的」(手机是拉起的卡片)、手机的导播设置 */}
      {data && world && <DirectorEngine world={data.world} civ={civ} off={directorOff} stepwise={stepWorld} />}
      {data && world && <DirectorPanels phone={narrow} civ={civ} hidden={directorOff} />}
      {data && world && civ && narrow && <ExtendSheet end={civ.endYear} hidden={!extendShown} />}
      {/* 逐年推演:往下走(不画东西)、手机停一下时的卡片、开始之前 / 推进设置 / 存回推演模式的窗口 */}
      {data && world && stepWorld && <StepwiseEngine world={data.world} civ={civ} />}
      {data && world && narrow && stepCard && <StepReviewSheet />}
      {data && world && <StepStartDialog phone={narrow} civ={civ} />}
      {data && world && stepOn && <StepSaveDialog phone={narrow} />}
      {data && world && stepOn && <StepRewindDialog phone={narrow} civ={civ} />}
      {data && world && stepOn && <StepBranchDeleteDialog phone={narrow} civ={civ} />}
      {/* 详情面板:窄屏是从屏幕底升起的卡片(在这儿的空位里),宽屏在侧栏里(见上面的 inspectorHost) */}
      {data && world && createPortal(<Inspector civ={civ} raw={shownRaw} raster={data.raster} world={data.world} />, inspectorHost)}
      {narrow && world && <div className="inspector-slot" ref={inspectorSlot} />}
      {hover && world && <HoverCard info={hover.info} x={hover.x} y={hover.y} place={hover.place} />}
      {/* 世界概览(点左上角的世界名打开):国家 / 编年史 / 我的干预 / 世界设定 */}
      {world && (
        <WorldOverview
          params={params}
          data={data}
          baseWorld={baseData?.world ?? null}
          civ={civ}
          generating={!!progress}
          resimBusy={!!resim}
          replay={{ on: replayOn, ready: !!replay }}
          onReplay={startReplay}
          onDraftFrom={draftFromCurrent}
        />
      )}
      {realCiv && <HistoryBook civ={realCiv} />}
      <AiSettingsHost />
      <AccountHost phone={narrow} />
      <FrozenAsk phone={narrow} />
      <ShortcutsHost />
      <DiagHost />
      <TipLayer />
      {newDlg && home && <NewWorldDialog key={newDlg.stamp ?? 0} phone={narrow} init={newDlg.init} shared={newDlg.shared} randomSeed={randomSeedValue} onCancel={cancelDialog} onStart={startFromDialog} />}
      {dropping && (
        <div className="drop-hint">
          <div>{dropping === 'image' ? '松手导入这张图' : '松手打开存档(.json)'}</div>
        </div>
      )}
    </div>
  );
}

/** 按下到松开移动不超过这么多(屏幕像素,横 + 竖)算单击 */
const CLICK_SLOP = 5;
/** 手指按下时总会抖一点:移动不超过这么多还算"点一下" */
const TOUCH_SLOP = 10;

/**
 * 只露出视窗(外框 ∩ 舞台)里的那一段 —— 主图和右边接的那一份在视窗外的部分裁掉,同一个地方不会出现两次。
 * clip-path 在地图层自己的坐标里(缩放、平移之前)。还没有世界时不裁
 */
function wrapClip(v: { k: number; x: number; y: number }, b: StageBox, wrap: number): string | undefined {
  if (!wrap || !b.sw || !b.bw) return undefined;
  const [wl, wr] = windowSpan(v.k, b);
  const l = (wl - v.x) / v.k;
  const r = b.sw - (wr - v.x) / v.k;
  return `inset(-100000px ${r}px -100000px ${l}px)`;
}

/** 屏幕层(不缩放,铺满舞台)按同一个视窗裁:舞台坐标 */
function screenClip(v: { k: number }, b: StageBox, wrap: number): string | undefined {
  if (!wrap || !b.sw || !b.bw) return undefined;
  const [wl, wr] = windowSpan(v.k, b);
  return `inset(0px ${b.sw - wr}px 0px ${wl}px)`;
}
