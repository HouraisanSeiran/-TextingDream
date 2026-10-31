// URL compatibility belongs here, independent of the App component and its workers.
import { DEFAULT_PARAMS, type WorldParams } from '../gen/world';
import { PARAM_RANGE, isShareHash, isMomentHash, decodeMomentHash, isContourKind, GEN_KEY } from '../gen/savefile';
import { cleanEndYear } from '../gen/edits';
import { LAYERS, type LayerId } from '../render/layers';
import { wrapLon } from '../render/projection';
import type { SurfaceLook } from '../render/surface';
import { galleryOfUrl } from '../account/gallery';
import { isPresetHash } from './presetLink';
import { GLOBE_READY, isMapProjection, isGraticuleStep, type MapProjection } from './projection';
import { mapViewFromUrl, baseLook, type Style, type SatLook } from './mapLayers';

export function readUrl(url: Pick<Location, 'search' | 'hash'> = location) {
  const q = new URLSearchParams(url.search);
  const params: WorldParams = { ...DEFAULT_PARAMS };
  for (const k of Object.keys(DEFAULT_PARAMS) as (keyof WorldParams)[]) {
    const v = q.get(k);
    // 和读存档一样:超出合理范围的调回范围内(手改的网址里可能是 0 或特别大的数)
    const n = v === null || v.trim() === '' ? NaN : Number(v);
    if (Number.isFinite(n)) params[k] = Math.min(PARAM_RANGE[k][1], Math.max(PARAM_RANGE[k][0], n));
  }
  // 底图 / 填色:新链接是 map=、fill=、sat=;旧链接的 style=、layer=、civ= 照旧认(实景 = 经典卫星;见 mapLayers.ts)
  const qs = q.get('style');
  const ql = q.get('layer');
  const mapView = mapViewFromUrl(q);
  let style: Style = qs === 'realistic' || qs === 'data' ? qs : 'fantasy';
  let layer: LayerId = LAYERS.some((l) => l.id === ql) ? (ql as LayerId) : 'biomes';
  // 卫星画法:网址里有就照它;旧链接的写实按经典;都没有 = 细节(新的默认)
  const sat: SatLook = mapView?.sat ?? (qs === 'realistic' ? 'classic' : 'detail');
  let surface: SurfaceLook = sat;
  if (mapView) {
    const b = baseLook(mapView.base, sat);
    style = b.style;
    if (b.data) layer = b.data;
    if (b.look) surface = b.look;
  }
  // 分享链接:# 后面是整份存档(gen/savefile.ts 的 encodeShare)
  const share = isShareHash(url.hash) ? url.hash : null;
  // 分享短链接(网站/s/<码> 转过来的 ?s=<码>):存档在服务器上,打开时去取;# 后面可以带着"打开时看哪"(#at=…,不经服务器)
  const shortShare = q.get('s');
  const moment = shortShare !== null && isMomentHash(url.hash) ? decodeMomentHash(url.hash) : null;
  // 朋友的预设链接(#preset=…,ui/presetLink.ts):打开就是填好参数的新建弹窗
  const preset = isPresetHash(url.hash) ? url.hash : null;
  // 作品墙(Gallery.tsx):作品墙那一页 / 打开一个作品
  const gallery = galleryOfUrl(q, url.hash);
  // 投影、中央经线(改了就写进网址,刷新、复制网址都还在)
  // 地球仪以前写的是 view=globe,照样认
  const pq = q.get('proj') ?? (q.get('view') === 'globe' ? 'globe' : null);
  const proj: MapProjection = isMapProjection(pq) && (pq !== 'globe' || GLOBE_READY) ? pq : 'equirect';
  const lq = Number(q.get('lon'));
  const lon = q.get('lon') !== null && Number.isFinite(lq) ? wrapLon(lq) : null;
  // 经纬网:grat=1 = 每 30°(旧网址就是这样),grat=10 / 15 / 30 = 每隔几度;没有 = 关
  const gq0 = q.get('grat');
  const grat: number = gq0 === '1' ? 30 : isGraticuleStep(Number(gq0)) ? Number(gq0) : 0;
  // 等值线:iso=elev / temp / precip;没有 = 不画
  const iq = q.get('iso');
  const iso = isContourKind(iq) ? iq : null;
  // 生成器版本(gen=):这个网址是哪一版画出来的世界;和现在的不同,打开时说清变了什么。旧网址没有 = 不知道,不提示;
  // 带了却认不出(不是整数之类)当成第 0 版:认不出的旧版本,照样提示,也不当成没带 gen 的老网址
  const gq = q.get(GEN_KEY);
  const gen = gq === null ? null : /^\d{1,6}$/.test(gq) ? Number(gq) : 0;
  // 推演年数(years=):新建中、还没存下的世界(new=)刷新、后退回来还记得弹窗里开的年数
  const yq = q.get('years');
  const years = yq === null ? undefined : cleanEndYear(Number(yq));
  return { params, style, layer, surface, sat, mapView, share, shortShare, moment, preset, gallery, proj, lon, grat, iso, gen, years };
}

