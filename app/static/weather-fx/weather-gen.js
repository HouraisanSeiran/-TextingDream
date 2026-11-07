/*
 * 织梦 · 天气生成 JS 镜像（浏览器挂 window.WeatherGen，Node 用 module.exports）
 * 与 app/weather.py 同一算法、同一套整数哈希值噪波，逐字段一致（浮点容差 1e-6）。
 * 修改算法时两边必须同步改，并跑 tests/test_weather.py 的对比测试。
 */
(function (root) {
  'use strict';
  // Shared extension tables (tools/weather_mirror_tables.py).
  var EXTRA = {"temperate":{"spring":[0,0.25,0,0,0,0,0.03,0,0,0],"summer":[0,0,0,0,0,0,0.03,0.08,0,0],"autumn":[0,0.05,0.06,0,0,0,0,0,0,0],"winter":[0.2,0.2,0.12,0,0,0,0,0,0,0]},"continental":{"spring":[0,0.25,0.05,0.06,0,0,0.06,0,0,0],"summer":[0,0,0,0,0,0,0.05,0.1,0,0],"autumn":[0,0.1,0.08,0,0,0,0,0,0,0],"winter":[0.1,0.15,0.15,0,0,0,0,0,0,1]},"maritime":{"spring":[0,0.2,0,0,0,0,0,0,0.04,0],"summer":[0,0,0,0,0,0,0,0.04,0.04,0],"autumn":[0,0.1,0,0,0,0,0,0,0.04,0],"winter":[0,0.3,0,0,0,0,0,0,0.02,0]},"mediterranean":{"spring":[0,0.1,0,0,0,0,0,0,0,0],"summer":[0,0,0,0,0,0,0,0.12,0,0],"autumn":[0,0,0,0,0,0,0,0,0,0],"winter":[0,0.15,0,0,0,0,0,0,0,0]},"subtropical_monsoon":{"spring":[0,0,0.06,0,0,0,0,0,0.04,0],"summer":[0,0,0,0,0,0.25,0,0.1,0.06,0],"autumn":[0,0,0.06,0,0,0.2,0,0,0.04,0],"winter":[0.25,0.1,0.15,0,0,0,0,0,0,0]},"tropical":{"spring":[0,0,0,0,0,0,0,0.06,0.06,0],"summer":[0,0,0,0,0,0.25,0,0.03,0.08,0],"autumn":[0,0,0,0,0,0.3,0,0,0.06,0],"winter":[0,0,0,0,0,0,0,0,0.06,0]},"arid":{"spring":[0,0,0,0.12,0.12,0,0,0,0,0],"summer":[0,0,0,0.08,0.1,0,0,0.12,0,0],"autumn":[0,0,0,0.08,0.1,0,0,0,0,0],"winter":[0,0,0,0.06,0.06,0,0,0,0,0]},"highland":{"spring":[0,0.35,0,0,0,0,0,0,0,0],"summer":[0,0.3,0,0,0,0,0,0,0,0],"autumn":[0,0.3,0,0,0,0,0,0,0,0],"winter":[0,0.3,0,0,0,0,0,0,0,1]},"polar":{"spring":[0,0.15,0,0,0,0,0,0,0,0],"summer":[0,0.15,0,0,0,0,0,0,0,0],"autumn":[0,0.15,0,0,0,0,0,0,0,0],"winter":[0,0,0,0,0,0,0,0,0,1]}};
  var AEROSOL_OF = {"haze":["haze",0.2,0.75],"dust":["dust",0.15,0.55],"blowing_sand":["sand",0.3,0.4],"sandstorm":["sand",0.55,0.45]};
  var DUST_KINDS = ["dust","blowing_sand","sandstorm"];
  var HEAT_KINDS = ["clear","cloudy","heatwave","haze","dust"];
  var RAINBOW_KINDS = ["clear","cloudy","sunshower"];
  var LIQUID_KINDS = ["drizzle","rain","storm","sunshower","tornado"];
  var FOGGY = ["fog","rime","spirit_mist","miasma"];
  var CYC_SLOT_H = 240.0;
  var AEROSOL_TYPES = ["none","haze","dust","sand"];
  var CYCLONE_PHASES = ["none","outer","eyewall","eye"];
  var MAX_CONTEXTS = 128;
  var MAX_MEMO = 2048;
  var NATURAL = ["clear","cloudy","overcast","fog","drizzle","rain","storm","snow","blizzard","sleet","sandstorm","hail","aurora","freezing_rain","graupel","frost","rime","haze","dust","blowing_sand","typhoon","tornado","heatwave","sunshower"];
  var FANTASY = ["mana_storm","spirit_mist","miasma","ashfall"];
  var KINDS = ["clear","cloudy","overcast","fog","drizzle","rain","storm","snow","blizzard","sleet","sandstorm","hail","aurora","freezing_rain","graupel","frost","rime","haze","dust","blowing_sand","typhoon","tornado","heatwave","sunshower","mana_storm","spirit_mist","miasma","ashfall"];
  var SEASONS = ["spring","summer","autumn","winter"];
  var PRECIP_TYPES = ["none","rain","snow","sleet","hail","freezing_rain","graupel"];
  var PTYPE = {"drizzle":"rain","rain":"rain","storm":"rain","snow":"snow","blizzard":"snow","sleet":"sleet","hail":"hail","freezing_rain":"freezing_rain","graupel":"graupel","typhoon":"rain","tornado":"rain","sunshower":"rain"};
  var PTYPES_OF = {"storm":["rain","hail"],"tornado":["rain","hail"]};
  var WET_TYPES = ["rain","sleet","hail","freezing_rain","graupel"];
  var GROUND_NAMES = ["wetness","puddles","snow_cover","hail_cover","ash_cover","mana_residue","glaze","frost","rime","dust_cover","graupel"];
  var WINDOW_HOURS = 216;
  var SNOW_RELAX = 0.02;
  var FRONT_KMH = 35.0;
  var LAPSE_C_PER_M = 0.0065;
  var MOON_PERIOD_DAYS = 29.53;
  var TAU = 2 * Math.PI;
  // 每季：[tlo, thi, wet, cloud, storm, fog, wind, dust, snow, aurora]（同 weather.py CLIMATES）
  var CLIMATES = {"temperate":{"dir":80,"elev":200,"spring":[4,15,0.32,0.55,0.1,0.15,0.35,0,0,0],"summer":[16,28,0.3,0.45,0.3,0.08,0.25,0,0,0],"autumn":[6,17,0.33,0.55,0.08,0.25,0.35,0,0,0],"winter":[-5,4,0.28,0.6,0,0.25,0.4,0,0.25,0]},"continental":{"dir":100,"elev":300,"spring":[0,13,0.25,0.5,0.08,0.1,0.45,0,0.1,0],"summer":[14,28,0.25,0.4,0.28,0.05,0.3,0,0,0],"autumn":[0,12,0.22,0.5,0.05,0.15,0.4,0,0.05,0],"winter":[-20,-8,0.22,0.55,0,0.15,0.45,0,0.6,0.35]},"maritime":{"dir":70,"elev":100,"spring":[5,13,0.42,0.7,0.04,0.2,0.5,0,0,0],"summer":[11,19,0.38,0.65,0.06,0.15,0.4,0,0,0],"autumn":[7,14,0.5,0.75,0.05,0.25,0.55,0,0,0],"winter":[1,7,0.5,0.78,0.03,0.25,0.6,0,0.05,0]},"mediterranean":{"dir":150,"elev":200,"spring":[10,20,0.2,0.4,0.06,0.08,0.3,0,0,0],"summer":[19,31,0.04,0.15,0.04,0.03,0.3,0,0,0],"autumn":[13,23,0.22,0.4,0.1,0.08,0.3,0,0,0],"winter":[5,13,0.38,0.6,0.04,0.12,0.4,0,0,0]},"subtropical_monsoon":{"dir":330,"elev":200,"spring":[13,22,0.4,0.65,0.12,0.2,0.3,0,0,0],"summer":[25,33,0.5,0.65,0.4,0.05,0.3,0,0,0],"autumn":[16,25,0.22,0.45,0.1,0.1,0.3,0,0,0],"winter":[3,11,0.22,0.6,0.02,0.25,0.35,0,0.02,0]},"tropical":{"dir":260,"elev":200,"spring":[23,32,0.3,0.5,0.35,0.05,0.25,0,0,0],"summer":[23,30,0.55,0.75,0.45,0.05,0.3,0,0,0],"autumn":[23,31,0.45,0.65,0.4,0.05,0.3,0,0,0],"winter":[22,31,0.2,0.4,0.2,0.05,0.25,0,0,0]},"arid":{"dir":200,"elev":500,"spring":[14,30,0.04,0.2,0.03,0.01,0.45,0.25,0,0],"summer":[25,42,0.02,0.1,0.04,0,0.5,0.3,0,0],"autumn":[14,30,0.04,0.18,0.03,0.01,0.4,0.2,0,0],"winter":[3,18,0.06,0.25,0,0.03,0.4,0.12,0,0]},"highland":{"dir":90,"elev":3500,"spring":[-3,12,0.2,0.5,0.12,0.15,0.55,0.08,0.15,0.15],"summer":[5,18,0.35,0.6,0.3,0.15,0.45,0.03,0,0.05],"autumn":[-3,11,0.15,0.4,0.08,0.15,0.5,0.06,0.1,0.2],"winter":[-15,0,0.12,0.4,0,0.1,0.6,0.1,0.5,0.3]},"polar":{"dir":240,"elev":100,"spring":[-25,-12,0.2,0.6,0,0.15,0.6,0,0.9,0.6],"summer":[-2,5,0.28,0.7,0,0.3,0.5,0,0.4,0.1],"autumn":[-18,-7,0.25,0.65,0,0.2,0.6,0,0.8,0.75],"winter":[-38,-26,0.18,0.55,0,0.1,0.65,0,0.95,0.95]}};
  var CLIMATE_NAMES = Object.keys(CLIMATES);
  var SEGMENTS = [[15, 90, 'winter', 'spring'], [105, 92, 'spring', 'summer'],
    [197, 91, 'summer', 'autumn'], [288, 92, 'autumn', 'winter']];
  var DEFAULT_INTENSITY = {"clear":[0.02,0.25],"cloudy":[0.35,0.65],"overcast":[0.75,0.95],"fog":[0.4,0.9],"drizzle":[0.08,0.28],"rain":[0.35,0.85],"storm":[0.3,0.9],"snow":[0.2,0.7],"blizzard":[0.65,1.0],"sleet":[0.2,0.6],"sandstorm":[0.4,0.9],"hail":[0.35,0.85],"aurora":[0.4,0.9],"mana_storm":[0.3,0.9],"spirit_mist":[0.3,0.8],"miasma":[0.3,0.8],"ashfall":[0.3,0.8],"freezing_rain":[0.2,0.7],"graupel":[0.2,0.7],"frost":[0.3,0.8],"rime":[0.3,0.8],"haze":[0.3,0.8],"dust":[0.3,0.7],"blowing_sand":[0.3,0.7],"typhoon":[0.4,0.9],"tornado":[0.4,0.9],"heatwave":[0.3,0.8],"sunshower":[0.2,0.6]};
  var BIOMES = ["海洋","湖泊","海冰","冰原","苔原","针叶林","寒漠","温带荒漠","草原","温带森林","温带雨林","热带荒漠","稀树草原","热带季雨林","热带雨林","湿地"];
  var BIOME_CLIMATE = {"海洋":null,"湖泊":null,"海冰":"polar","冰原":"polar","苔原":"polar","针叶林":"continental","寒漠":"arid","温带荒漠":"arid","草原":"continental","温带森林":"temperate","温带雨林":"maritime","热带荒漠":"arid","稀树草原":"tropical","热带季雨林":"tropical","热带雨林":"tropical","湿地":null};
  var CLOUD_BAND = {"clear":[0.0,0.3],"cloudy":[0.3,0.7],"overcast":[0.7,1.0]};
  var RELATED = {"clear":["cloudy","overcast"],"cloudy":["clear","overcast"],"overcast":["cloudy","clear","drizzle"],"fog":["overcast","cloudy","clear"],"drizzle":["rain","sleet","snow"],"rain":["snow","sleet","storm","drizzle"],"storm":["rain","hail","blizzard","snow"],"snow":["sleet","rain"],"blizzard":["snow","storm","rain"],"sleet":["rain","snow"],"sandstorm":["clear","cloudy"],"hail":["storm","rain","sleet"],"aurora":["clear","cloudy"],"mana_storm":["overcast","storm"],"spirit_mist":["fog","overcast"],"miasma":["fog","overcast"],"ashfall":["overcast","cloudy"],"freezing_rain":["sleet","rain","snow"],"graupel":["snow","sleet","hail"],"frost":["clear","cloudy"],"rime":["fog","frost"],"haze":["fog","cloudy","clear"],"dust":["blowing_sand","haze","clear"],"blowing_sand":["dust","sandstorm"],"typhoon":["storm","rain"],"tornado":["storm","hail","rain"],"heatwave":["clear","cloudy"],"sunshower":["rain","drizzle","clear"]};
  var OVERRIDE_FIELDS = {"intensity":[0,1],"cloud_cover":[0,1],"fog":[0,1],"humidity":[0,1],"visibility":[0,1],"lightning":[0,1],"temperature_c":[-80,60],"rainbow":[0,1],"heat":[0,1],"vortex":[0,1]};
  var GROUND_RANGES = {};
  for (var gi = 0; gi < GROUND_NAMES.length; gi++) GROUND_RANGES[GROUND_NAMES[gi]] = [0, 1];
  var OVERRIDE_NESTED = {"wind":{"dir_deg":[0,360],"speed":[0,1],"gust":[0,1]},"precipitation":{"type":["none","rain","snow","sleet","hail","freezing_rain","graupel"],"rate":[0,1]},"ground":{"wetness":[0,1],"puddles":[0,1],"snow_cover":[0,1],"hail_cover":[0,1],"ash_cover":[0,1],"mana_residue":[0,1],"glaze":[0,1],"frost":[0,1],"rime":[0,1],"dust_cover":[0,1],"graupel":[0,1]},"aurora":{"strength":[0,1],"hue":[0,1]},"magic":{"strength":[0,1],"hue":[0,1],"pulse":[0,1]},"aerosol":{"type":["none","haze","dust","sand"],"density":[0,1]},"cyclone":{"category":[1,5],"phase":["outer","eyewall","eye"]}};
  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }

  // ------------------------------------------------------------ integer-hash value noise
  function h32(x) { // same as WeatherNoise.hash32 and weather.py _h32
    x |= 0;
    x = Math.imul(x ^ (x >>> 16), 0x45d9f3b);
    x = Math.imul(x ^ (x >>> 16), 0x45d9f3b);
    return (x ^ (x >>> 16)) >>> 0;
  }
  function key(seed, ch) { return h32((seed + (ch + 1) * 0x9E3779B1) >>> 0); }
  function lattice(k, i) { return h32((k + Math.imul(i, 0x85EBCA6B)) >>> 0) / 4294967296.0; }
  function vn(k, x) {
    var i = Math.floor(x), f = x - i, a = lattice(k, i), b = lattice(k, i + 1);
    return a + (b - a) * (f * f * (3 - 2 * f));
  }
  function lattice2(k, i, j) {
    return h32((k + Math.imul(i, 0x85EBCA6B) + Math.imul(j, 0xC2B2AE35)) >>> 0) / 4294967296.0;
  }
  function vn2(k, x, y) { // 2D value noise (smoothstep-bilinear), weather.py _vn2
    var i = Math.floor(x), j = Math.floor(y), fx = sm(x - i), fy = sm(y - j);
    var a = lattice2(k, i, j), b = lattice2(k, i + 1, j), c = lattice2(k, i, j + 1), d = lattice2(k, i + 1, j + 1);
    var top = a + (b - a) * fx, bot = c + (d - c) * fx;
    return top + (bot - top) * fy;
  }
  function sm(f) { return f * f * (3 - 2 * f); }
  function sig(seed, ch, t, p1, p2) {
    return 0.65 * vn(key(seed, ch), t / p1) + 0.35 * vn(key(seed, ch + 50), t / p2);
  }
  function u(seed, ch, t, p1, p2) { return cdf(sig(seed, ch, t, p1, p2)); }
  var Q = [0.0, 0.1991, 0.2557, 0.2972, 0.3319, 0.3627, 0.3916, 0.4192, 0.4465, 0.4733, 0.4997,
    0.5261, 0.5529, 0.5801, 0.6083, 0.6374, 0.6687, 0.7039, 0.7455, 0.8020, 1.0];
  function cdf(x) {
    if (x <= Q[0]) return 0.0;
    if (x >= Q[20]) return 1.0;
    var k = 0;
    while (x > Q[k + 1]) k += 1;
    return (k + (x - Q[k]) / (Q[k + 1] - Q[k])) / 20;
  }
  function clamp01(x) { return Math.min(1.0, Math.max(0.0, x)); }
  function clamp(x, lo, hi) { return Math.min(hi, Math.max(lo, x)); }
  function mod(x, m) { var r = x % m; if (r < 0) r += m; return r; }

  function params(climate, season, doy0, south) {
    var table = CLIMATES[climate];
    if (season != null) return [table[season], season];
    var x = doy0;
    if (south) x = mod(x + 182.5, 365);
    if (x < 15) x += 365;
    for (var j = 0; j < SEGMENTS.length; j++) {
      var g = SEGMENTS[j], start = g[0], length = g[1];
      if (x < start + length) {
        var f = (x - start) / length, s = f * f * (3 - 2 * f);
        var pa = table[g[2]], pb = table[g[3]], vals = [];
        for (var i = 0; i < 10; i++) vals.push(pa[i] + (pb[i] - pa[i]) * s);
        return [vals, x - start < length / 2 ? g[2] : g[3]];
      }
    }
    return [table.winter, 'winter'];
  }
  function lv(x, share, floor) {
    if (floor == null) floor = 0.25;
    if (share <= 0 || x <= 1 - share) return 0.0;
    return Math.min(1.0, (x - (1 - share)) / Math.max(share, floor));
  }
  function ext(base, more) { var o = {}, k; for (k in base) o[k] = base[k]; for (k in more) o[k] = more[k]; return o; }
  var NO_PRECIP = { 'precipitation.rate': [0, 0], lightning: [0, 0] };
  var KIND_RANGE = {"clear":{"precipitation.rate":[0,0],"lightning":[0,0],"intensity":[0,0.3],"cloud_cover":[0,0.3],"fog":[0,0.3],"visibility":[0.5,1],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,1],"rainbow":[0,1]},"cloudy":{"precipitation.rate":[0,0],"lightning":[0,0],"intensity":[0.3,0.7],"cloud_cover":[0.3,0.7],"fog":[0,0.35],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,1],"rainbow":[0,1]},"overcast":{"precipitation.rate":[0,0],"lightning":[0,0],"intensity":[0.7,1],"cloud_cover":[0.7,1],"fog":[0,0.4],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"fog":{"precipitation.rate":[0,0],"lightning":[0,0],"fog":[0.3,1],"humidity":[0.7,1],"visibility":[0,0.7],"wind.speed":[0,0.35],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"drizzle":{"temperature_c":[0,60],"precipitation.rate":[0.01,0.4],"cloud_cover":[0.6,1],"humidity":[0.6,1],"lightning":[0,0],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"rain":{"temperature_c":[0,60],"precipitation.rate":[0.05,1],"cloud_cover":[0.6,1],"humidity":[0.6,1],"lightning":[0,0],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"storm":{"temperature_c":[2,60],"precipitation.rate":[0.05,1],"cloud_cover":[0.7,1],"humidity":[0.6,1],"lightning":[0.05,1],"wind.speed":[0.4,1],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"snow":{"temperature_c":[-80,1],"precipitation.rate":[0.02,1],"cloud_cover":[0.6,1],"lightning":[0,0],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"blizzard":{"temperature_c":[-80,1],"precipitation.rate":[0.3,1],"cloud_cover":[0.7,1],"lightning":[0,0],"wind.speed":[0.5,1],"visibility":[0,0.4],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"sleet":{"temperature_c":[-3,4],"precipitation.rate":[0.02,1],"cloud_cover":[0.6,1],"lightning":[0,0],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"sandstorm":{"precipitation.rate":[0,0],"lightning":[0,0],"fog":[0,0.2],"humidity":[0,0.5],"visibility":[0,0.5],"wind.speed":[0.45,1],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"hail":{"temperature_c":[-5,45],"precipitation.rate":[0.05,1],"cloud_cover":[0.7,1],"humidity":[0.6,1],"wind.speed":[0.3,1],"lightning":[0,0],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"aurora":{"precipitation.rate":[0,0],"lightning":[0,0],"intensity":[0.2,1],"cloud_cover":[0,0.5],"fog":[0,0.3],"aurora.strength":[0,1],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"mana_storm":{"precipitation.rate":[0,0],"lightning":[0,0],"cloud_cover":[0.6,1],"wind.speed":[0.3,1],"magic.strength":[0.1,1],"aurora.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"spirit_mist":{"precipitation.rate":[0,0],"lightning":[0,0],"fog":[0.3,1],"visibility":[0,0.7],"wind.speed":[0,0.4],"magic.strength":[0.05,1],"aurora.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"miasma":{"precipitation.rate":[0,0],"lightning":[0,0],"fog":[0.3,1],"humidity":[0.6,1],"visibility":[0,0.6],"wind.speed":[0,0.35],"aurora.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"ashfall":{"precipitation.rate":[0,0],"lightning":[0,0],"cloud_cover":[0.6,1],"visibility":[0,0.8],"aurora.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"freezing_rain":{"temperature_c":[-4,0],"precipitation.rate":[0.02,1],"cloud_cover":[0.6,1],"lightning":[0,0],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"graupel":{"temperature_c":[-2,3],"precipitation.rate":[0.02,1],"cloud_cover":[0.6,1],"lightning":[0,0],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"frost":{"precipitation.rate":[0,0],"lightning":[0,0],"temperature_c":[-80,0],"cloud_cover":[0,0.3],"wind.speed":[0,0.25],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"rime":{"precipitation.rate":[0,0],"lightning":[0,0],"temperature_c":[-80,-2],"fog":[0.3,1],"humidity":[0.8,1],"wind.speed":[0,0.4],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"haze":{"precipitation.rate":[0,0],"lightning":[0,0],"wind.speed":[0,0.3],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,1],"rainbow":[0,0]},"dust":{"precipitation.rate":[0,0],"lightning":[0,0],"humidity":[0,0.5],"wind.speed":[0.1,0.6],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,1],"rainbow":[0,0]},"blowing_sand":{"precipitation.rate":[0,0],"lightning":[0,0],"humidity":[0,0.4],"wind.speed":[0.35,0.8],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"typhoon":{"temperature_c":[15,45],"precipitation.rate":[0.01,1],"wind.speed":[0.7,1],"lightning":[0,0],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,0]},"tornado":{"temperature_c":[2,45],"precipitation.rate":[0.05,1],"cloud_cover":[0.7,1],"wind.speed":[0.7,1],"lightning":[0,0],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,1],"heat":[0,0],"rainbow":[0,0]},"heatwave":{"precipitation.rate":[0,0],"lightning":[0,0],"temperature_c":[25,60],"cloud_cover":[0,0.35],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,1],"rainbow":[0,0]},"sunshower":{"temperature_c":[2,45],"precipitation.rate":[0.01,0.5],"cloud_cover":[0.05,0.49],"lightning":[0,0],"aurora.strength":[0,0],"magic.strength":[0,0],"vortex":[0,0],"heat":[0,0],"rainbow":[0,1]}};
  var AURORA_KINDS = ['clear', 'cloudy', 'aurora'];
  for (var kr in KIND_RANGE) {
    if (AURORA_KINDS.indexOf(kr) < 0 && !has(KIND_RANGE[kr], 'aurora.strength')) KIND_RANGE[kr]['aurora.strength'] = [0, 0];
    if (FANTASY.indexOf(kr) < 0 && !has(KIND_RANGE[kr], 'magic.strength')) KIND_RANGE[kr]['magic.strength'] = [0, 0];
  }
  var CLOUD_OF = {"drizzle":[0.7,0.25],"rain":[0.8,0.2],"storm":[0.85,0.15],"snow":[0.75,0.25],"blizzard":[0.9,0.1],"sleet":[0.8,0.2],"hail":[0.85,0.15],"mana_storm":[0.7,0.3],"ashfall":[0.75,0.25],"freezing_rain":[0.75,0.25],"graupel":[0.7,0.25],"frost":[0.05,0.1],"rime":[0.45,0.3],"haze":[0.3,0.2],"dust":[0.2,0.15],"blowing_sand":[0.2,0.2],"typhoon":[0.8,0.2],"tornado":[0.85,0.15],"heatwave":[0.05,0.15],"sunshower":[0.1,0.3]};
  var FOG_OF = {"fog":[0.4,0.6],"drizzle":[0.15,0.2],"rain":[0.08,0.1],"storm":[0.1,0],"snow":[0.1,0.25],"blizzard":[0.35,0.4],"sleet":[0.15,0],"hail":[0.05,0],"spirit_mist":[0.35,0.6],"miasma":[0.3,0.65],"ashfall":[0.15,0.25],"mana_storm":[0.1,0.1],"rime":[0.35,0.5]};
  var WIND_FLOOR = {"storm":[0.45,0.5],"blizzard":[0.45,0.5],"sandstorm":[0.45,0.5],"hail":[0.35,0.4],"mana_storm":[0.35,0.5],"typhoon":[0.7,0.3],"tornado":[0.7,0.3],"blowing_sand":[0.35,0.35]};
  var RATE = {"drizzle":0.3,"rain":1.0,"storm":1.0,"snow":0.8,"blizzard":1.0,"sleet":0.7,"hail":0.8,"freezing_rain":0.65,"graupel":0.7,"typhoon":1.0,"tornado":1.0,"sunshower":0.4};
  var VCOST = {"drizzle":0.25,"rain":0.3,"storm":0.4,"snow":0.5,"blizzard":0.4,"sleet":0.35,"hail":0.35,"freezing_rain":0.35,"graupel":0.4,"typhoon":0.65,"tornado":0.6,"sunshower":0.2};
  var FANTASY_SHARE = {"mana_storm":0.06,"spirit_mist":0.08,"miasma":0.08,"ashfall":0.05};
  var MAGIC_OF = {"mana_storm":[0.2,0.8],"spirit_mist":[0.15,0.6],"miasma":[0,0.3],"ashfall":[0,0.4]};
  var MAGIC_HUE = {"mana_storm":[0.72,0.25],"spirit_mist":[0.3,0.35],"miasma":[0.22,0.06],"ashfall":[0.05,0.05]};
  var MAGIC_PULSE = {"mana_storm":[0.4,0.6],"spirit_mist":[0.15,0.25],"miasma":[0.05,0.1],"ashfall":[0.2,0.5]};
  var TWILIGHT_H = 1.5;
  var DRIFT_H_PER_DEG = 111.32 * 0.7 / FRONT_KMH;
  var OFFSET_H = 12.0, SPATIAL_DEG = 20.0;

  var CONTEXTS = new Map(), naturalEvaluations = 0;
  function memoPut(cache, k, v, limit) {
    cache[k] = v;
    var keys = Object.keys(cache);
    if (keys.length > (limit || MAX_MEMO)) delete cache[keys[0]];
    return v;
  }
  function clearCache() { CONTEXTS.clear(); naturalEvaluations = 0; }
  function cacheInfo() { return {contexts: CONTEXTS.size, max_contexts: MAX_CONTEXTS,
    max_entries_per_context: MAX_MEMO, natural_evaluations: naturalEvaluations}; }
  function flowDirection(c) {
    if (c.lat == null) return CLIMATES[c.climate].dir;
    var a = Math.abs(c.lat), west = sm(clamp01((a - 25) / 10)) * (1 - sm(clamp01((a - 55) / 10)));
    return 270 - 180 * west;
  }
  function vn3(k, x, y, z) {
    var ix = Math.floor(x), iy = Math.floor(y), iz = Math.floor(z), fx = sm(x - ix), fy = sm(y - iy), fz = sm(z - iz);
    function plane(kz) {
      var pk = (k + Math.imul(kz, 0x27D4EB2D)) >>> 0;
      var a = lattice2(pk, mod(ix, 18), iy), b = lattice2(pk, mod(ix + 1, 18), iy);
      var d = lattice2(pk, mod(ix, 18), iy + 1), e = lattice2(pk, mod(ix + 1, 18), iy + 1);
      return a + (b - a) * fx + ((d + (e - d) * fx) - (a + (b - a) * fx)) * fy;
    }
    var a = plane(iz), b = plane(iz + 1);
    return a + (b - a) * fz;
  }
  function signal(c, ch, t, p1, p2) {
    if (c.lat == null || c.lon == null) return u(c.hs, ch, t, p1, p2);
    var direction = flowDirection(c) * Math.PI / 180;
    var east = Math.sin(direction) * FRONT_KMH / (111.32 * Math.max(.2, Math.cos(c.lat * Math.PI / 180)));
    var north = Math.cos(direction) * FRONT_KMH / 111.32;
    var x = (c.lon - east * t) / 20, y = (c.lat - north * t) / 20;
    return cdf(.65 * vn3(key(c.hs, ch), x, y, t / (4 * p1)) + .35 * vn3(key(c.hs, ch + 50), x, y, t / (4 * p2)));
  }
  function extraParams(c, t) {
    var table = EXTRA[c.climate];
    if (c.season != null) return table[c.season];
    var x = mod(c.start - 1 + t / 24 + (c.south ? 182.5 : 0), 365);
    if (x < 15) x += 365;
    for (var j = 0; j < SEGMENTS.length; j++) {
      var sg = SEGMENTS[j];
      if (x < sg[0] + sg[1]) {
        var f = sm((x - sg[0]) / sg[1]);
        return table[sg[2]].map(function(v, i) { return v + (table[sg[3]][i] - v) * f; });
      }
    }
    return table.winter;
  }

  function conflict(kind, ov) {
    if (has(ov, 'precipitation.type') && has(ov, 'precipitation.rate') &&
        ((ov['precipitation.type'] === 'none') !== (ov['precipitation.rate'] === 0))) return 'precipitation.type 为 none 当且仅当 rate 为 0';
    var allowed = kind === 'typhoon' && ov['cyclone.phase'] === 'eye' ? ['none', 'rain'] :
      (PTYPES_OF[kind] || [PTYPE[kind] || 'none']);
    if (has(ov, 'precipitation.type') && allowed.indexOf(ov['precipitation.type']) < 0) return 'precipitation.type 与 kind 不一致';
    var ranges = KIND_RANGE[kind];
    for (var f in ranges) {
      var r = ranges[f];
      if (kind === 'typhoon' && ov['cyclone.phase'] === 'eye' && ['wind.speed', 'precipitation.rate'].indexOf(f) >= 0) r = [0, .3];
      if (has(ov, f) && (ov[f] < r[0] || ov[f] > r[1])) return kind + ' 要求 ' + f + ' 在 [' + r[0] + ', ' + r[1] + ']';
    }
    if (Object.keys(ov).some(function(k) { return k.indexOf('cyclone.') === 0; }) && kind !== 'typhoon') return 'cyclone 只能用于 typhoon';
    var atype = (AEROSOL_OF[kind] || ['none', 0, 0])[0];
    if (has(ov, 'aerosol.type') && ov['aerosol.type'] !== atype) return 'aerosol.type 与 kind 不一致';
    if (atype === 'none' && (ov['aerosol.density'] || 0) > 0) return '该 kind 不支持 aerosol.density';
    return null;
  }
  function ramp(u, share) {
    if (share <= 0) return 0.0;
    return clamp01((u - (1 - share) + 0.35) / 0.35);
  }
  function fit(kind, name, v) {
    var r = KIND_RANGE[kind][name] || (name === 'temperature_c' ? [-80, 60] : null);
    return r ? clamp(v, r[0], r[1]) : v;
  }

  // ------------------------------------------------------------ calendar / solar (geography.py)
  function checkCalendar(cal) {
    var out = { start_day_of_year: 80, utc_offset: 0, axial_tilt_deg: 23.44, enabled: true };
    if (cal == null || typeof cal !== 'object') throw new Error('calendar 必须是对象');
    for (var k in cal) {
      if (!has(out, k)) throw new Error('calendar 不支持字段 ' + k);
      out[k] = cal[k];
    }
    var s = out.start_day_of_year;
    if (typeof s !== 'number' || Math.floor(s) !== s || s < 1 || s > 365) throw new Error('calendar.start_day_of_year 必须是 1..365 的整数');
    if (typeof out.utc_offset !== 'number' || !isFinite(out.utc_offset) || out.utc_offset < -12 || out.utc_offset > 14)
      throw new Error('calendar.utc_offset 超出 [-12, 14]');
    if (typeof out.axial_tilt_deg !== 'number' || !isFinite(out.axial_tilt_deg) || out.axial_tilt_deg < 0 || out.axial_tilt_deg > 45)
      throw new Error('calendar.axial_tilt_deg 超出 [0, 45]');
    if (typeof out.enabled !== 'boolean') throw new Error('calendar.enabled 必须是布尔值');
    return out;
  }
  function roundHalfEven(x) { // Python round()
    var r = Math.round(x);
    if (Math.abs(x - Math.floor(x) - 0.5) === 0 && r % 2 !== 0) r -= 1;
    return r;
  }
  var DEG = Math.PI / 180;
  function solar(latitude, longitude, day, calendar) {
    var cfg = checkCalendar(calendar);
    if (!cfg.enabled) return null;
    var doy = mod(cfg.start_day_of_year + day - 2, 365) + 1;
    var phi = latitude * DEG;
    var decl = cfg.axial_tilt_deg * DEG * Math.sin(2 * Math.PI * (284 + doy) / 365);
    var b = 2 * Math.PI * (doy - 81) / 364;
    var equation = 9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b);
    var noon = 12 + cfg.utc_offset - longitude / 15 - equation / 60;
    var den = Math.cos(phi) * Math.cos(decl);
    var num = Math.sin(-0.833 * DEG) - Math.sin(phi) * Math.sin(decl);
    var ratio = Math.abs(den) > 1e-12 ? num / den : (num > 0 ? Infinity : -Infinity);
    var duration, polar = null;
    if (ratio >= 1) { duration = 0; polar = 'polar_night'; }
    else if (ratio <= -1) { duration = 24; polar = 'polar_day'; }
    else duration = 2 * (Math.acos(ratio) / DEG) / 15; // math.degrees(x) = x / (pi/180) in CPython
    function clock(h) { // hours as weather.py _clock(geography clock(h)) would give
      var m = roundHalfEven(h * 60);
      return Math.floor(mod(m, 1440) / 60) + mod(m, 60) / 60 + 24 * Math.floor(m / 1440);
    }
    return { polar: polar, sunrise: polar ? null : clock(noon - duration / 2), sunset: polar ? null : clock(noon + duration / 2) };
  }

  // seed = the caller's integer (reported in the state); hashing uses it mod 2^32 like weather.py & M32.
  function Ctx(seed, climate, season, lat, lon, calendar, fantasy, elevation, coastDistance) {
    this.seed = seed; this.hs = seed >>> 0; this.climate = climate; this.season = season;
    this.lat = lat; this.lon = lon; this.calendar = calendar; this.fantasy = fantasy;
    this.coast_distance_km = coastDistance;
    this.south = lat != null && lat < 0;
    this.start = calendar != null ? checkCalendar(calendar).start_day_of_year : 1;
    this.lapse = elevation == null ? 0 : (elevation - CLIMATES[climate].elev) * LAPSE_C_PER_M;
    this.shift = 0;
    if (lat != null && lon != null) {
      var angle = lon * Math.PI / 180;
      var off = vn2(key(this.hs, 30), Math.cos(angle) * 3, Math.sin(angle) * 3 + lat / SPATIAL_DEG);
      this.shift = OFFSET_H * (2 * off - 1);
    }
    this.aurora_lat = lat == null ? 1 : clamp01((Math.abs(lat) - 50) / 15);
    this.cache = {}; this.suns = {}; this.gcache = {};
  }

  function sunOf(c, day) { // (sunrise, sunset) of game day; weather.py _sun
    if (has(c.suns, day)) return c.suns[day];
    var rs = [6.0, 18.0];
    if (c.calendar != null && c.lat != null && c.lon != null) {
      var sun = solar(c.lat, c.lon, day, c.calendar);
      if (sun !== null) {
        if (sun.polar === 'polar_day') rs = [0.0, 24.0];
        else if (sun.polar === 'polar_night') rs = [12.0, 12.0];
        else { var r0 = mod(sun.sunrise, 24.0); rs = [r0, r0 + (sun.sunset - sun.sunrise)]; }
      }
    }
    memoPut(c.suns,day,rs,128);
    return rs;
  }
  function dark(c, t) {
    var day = Math.floor(t / 24) + 1, h = t - (day - 1) * 24, rs = sunOf(c, day), rise = rs[0], sett = rs[1];
    if (sett - rise >= 24) return 0.0;
    if (sett <= rise) return 1.0;
    var dist = 24.0, xs = [h - 24, h, h + 24];
    for (var j = 0; j < 3; j++) {
      var x = xs[j];
      if (rise <= x && x <= sett) return 0.0;
      dist = Math.min(dist, Math.abs(x - rise), Math.abs(x - sett));
    }
    return clamp01(dist / TWILIGHT_H);
  }


  function cyclone(c, t, tendency) {
    var empty = {category: 0, phase: 'none'};
    if (tendency <= 0 || c.coast_distance_km == null || c.coast_distance_km > 200) return empty;
    var slot = Math.floor(t / CYC_SLOT_H), k = key(c.hs, 70);
    if (lattice(k, slot) >= tendency) return empty;
    var duration = 48 + 24 * lattice(k, slot + 100000);
    var start = slot * CYC_SLOT_H + (CYC_SLOT_H - duration) * lattice(k, slot + 200000);
    var progress = (t - start) / duration;
    if (progress < 0 || progress > 1) return empty;
    var lateral = c.lon == null || c.lat == null ? 0 : .7 * (2 * signal(c, 71, t, 160, 80) - 1);
    var radius = Math.sqrt(Math.pow(2 * progress - 1, 2) + lateral * lateral);
    return {category: 1 + Math.floor(5 * lattice(k, slot + 300000)),
      phase: radius < .16 ? 'eye' : (radius < .6 ? 'eyewall' : 'outer')};
  }

  function natural(c, t) {
    if (has(c.cache, t)) return c.cache[t];
    naturalEvaluations++;
    var hour = mod(t, 24), ts = t + c.shift;
    var pr = params(c.climate, c.season, mod(c.start - 1 + t / 24, 365), c.south), p = pr[0], label = pr[1];
    var tlo=p[0], thi=p[1], wet=p[2], cloud=p[3], storm=p[4], fogt=p[5], wind=p[6], dust=p[7], aur=p[9];
    var uf=signal(c,0,t,40,13), uc=signal(c,1,t,30,7), ucl=signal(c,2,t,30,9), ua=signal(c,3,t,96,30);
    var ufg=signal(c,4,t,30,12), uw=signal(c,5,t,24,6), ud=signal(c,6,t,36,10), uh=signal(c,10,t,20,6);
    var aft=.5+.5*Math.cos(TAU*(hour-16)/24), night=.5+.5*Math.cos(TAU*(hour-5)/24);
    var sshare=storm*.5*(.3+.7*aft), lp=lv(uf,wet), ls=lv(uc,sshare), ld=lv(ud,dust*.5), lf=lv(ufg,fogt*(.3+.7*night));
    var near=Math.max(ramp(uf,wet),ramp(uc,sshare)), cl=clamp01(cloud+(ucl-.5)*.7);
    cl+=(Math.max(cl,.85)-cl)*near;
    var ip=Math.max(lp,ls), temp=(tlo+thi)/2+(thi-tlo)/2*Math.cos(TAU*(hour-15)/24)*(1-.5*cl)+(ua-.5)*8-2*ip-1.5*Math.min(1,8*ip)-c.lapse;
    var ws=clamp01(wind*.8+(uw-.5)*.5+.3*lp+.35*ls+.5*ld), hail=ls>.3&&uh>.65, darkLevel=dark(c,t);
    var ar=lv(signal(c,11,t,30,8),aur*.7,.3)*darkLevel*c.aurora_lat, fl=0, fk=null;
    for(var j=0;j<FANTASY.length;j++) if(c.fantasy.indexOf(FANTASY[j])>=0) {
      var f=FANTASY[j], lvl=lv(signal(c,20+j,t,36,11),FANTASY_SHARE[f]);
      if(lvl>fl){fl=lvl;fk=f;}
    }
    var kind, intensity;
    if(fk!==null&&fl>.1){kind=fk;intensity=fl;}
    else if(ip>0){
      intensity=ip;
      if(temp<0)kind=ip>.55&&ws>.55?'blizzard':'snow';
      else if(temp<2)kind='sleet';
      else if(ls>.12&&ls>=.8*lp)kind=hail&&uh>.8?'hail':'storm';
      else kind=ip<.15?'drizzle':'rain';
    }else if(ld>.1){kind='sandstorm';intensity=ld;}
    else if(lf>.15&&ws<.35){kind='fog';intensity=lf;}
    else if(ar>.45&&cl<.5){kind='aurora';intensity=ar;}
    else{kind=cl<.3?'clear':(cl<.7?'cloudy':'overcast');intensity=cl;}
    var ex=extraParams(c,t), frz=ex[0],grp=ex[1],haze=ex[2],fdust=ex[3],blow=ex[4],typh=ex[5],torn=ex[6],heat=ex[7],sunsh=ex[8],rime=ex[9];
    var ux=signal(c,40,t,36,12), heatLevel=lv(signal(c,41,t,160,72),heat);
    temp+=10*heatLevel;
    var cyc=cyclone(c,t,typh);
    if(fk===null||fl<=.1){
      if(cyc.phase!=='none'){kind='typhoon';intensity=.45+.1*cyc.category;}
      else if(ip>0){
        if(temp>=-4&&temp<=0&&ux>1-frz)kind='freezing_rain';
        else if(temp>=-2&&temp<=3&&ux<grp)kind='graupel';
        else if(kind==='storm'&&ls>.3&&signal(c,42,t,2,.5)>1-torn)kind='tornado';
      }else if(ld<=.1&&lf<=.15){
        if(temp<-2&&darkLevel>0&&rime>0&&ufg>.7){kind='rime';intensity=.3+.6*ufg;}
        else if(temp<=0&&darkLevel>0&&ws<.25&&cl<.3){kind='frost';intensity=.2+.6*darkLevel;}
        else if(lv(ux,blow)>.05&&ws>.35){kind='blowing_sand';intensity=lv(ux,blow);}
        else if(lv(ud,fdust)>.05){kind='dust';intensity=lv(ud,fdust);}
        else if(lv(ux,haze)>.05&&ws<.3){kind='haze';intensity=lv(ux,haze);}
        else if(heatLevel>.1&&temp>=25){kind='heatwave';intensity=heatLevel;}
        else if(lv(ux,sunsh)>.05&&temp>2&&cl<.5){kind='sunshower';intensity=lv(ux,sunsh);}
      }
    }
    return memoPut(c.cache,t,{kind:kind,intensity:intensity,temp:temp,ws:ws,cl:cl,lf:lf,night:night,
      p:p,season:label,hail:hail,ar:ar,dark:darkLevel,ts:ts,t:t,cyclone:cyc});
  }

  function ptypeOf(kind, n, ov) {
    if (has(ov, 'precipitation.type')) return ov['precipitation.type'];
    if (kind === 'storm' && n.hail) return 'hail';
    return PTYPE[kind] || 'none';
  }
  function core(kind, intensity, n) { return groundInput(kind, intensity, n); }

  function chooseKind(c, n, ov) {
    if (has(ov, 'kind')) {
      var why = conflict(ov.kind, ov);
      if (why) throw new Error('覆盖字段互相矛盾：' + why);
      return ov.kind;
    }
    var order = [n.kind].concat(RELATED[n.kind], KINDS), first = null;
    for (var j = 0; j < order.length; j++) {
      var k = order[j];
      if (FANTASY.indexOf(k) >= 0 && c.fantasy.indexOf(k) < 0) continue;
      var w = conflict(k, ov);
      if (w === null) return k;
      first = first || w;
    }
    throw new Error('覆盖字段没有任何天气类型能同时满足：' + first);
  }

  function intensityOf(c, t, kind, n, ov) {
    if (has(ov, 'intensity')) return ov.intensity;
    var i;
    if (has(RATE, kind) && has(ov, 'precipitation.rate')) i = ov['precipitation.rate'] / RATE[kind];
    else if (has(CLOUD_BAND, kind) && has(ov, 'cloud_cover')) i = ov.cloud_cover;
    else if (kind === n.kind) i = n.intensity;
    else {
      var r = DEFAULT_INTENSITY[kind];
      i = r[0] + (r[1] - r[0]) * u(c.hs, 8, n.ts, 30, 10);
    }
    return fit(kind, 'intensity', clamp01(i));
  }

  var GROUND_KEYS = ["kind","intensity","precipitation.type","precipitation.rate","temperature_c","wind.speed","fog","humidity","cloud_cover","aerosol.density","cyclone.phase"];


  function groundInput(kind, intensity, n, fields) {
    var ptype,rate,temp,ws,cl,fg,hum;
    if(!fields){
      ptype=ptypeOf(kind,n,{});
      rate=has(RATE,kind)?fit(kind,'precipitation.rate',RATE[kind]*intensity):0;
      temp=fit(kind,'temperature_c',n.temp);
      var wind=WIND_FLOOR[kind]||[0,0],cloud=CLOUD_OF[kind]||[n.cl,0],fog=FOG_OF[kind]||[0,0];
      ws=fit(kind,'wind.speed',Math.max(n.ws,wind[0]+wind[1]*intensity));
      cl=fit(kind,'cloud_cover',cloud[0]+cloud[1]*intensity);
      fg=fit(kind,'fog',fog[0]+fog[1]*intensity);
      hum=FOGGY.indexOf(kind)>=0?.95:(has(RATE,kind)?.9:.5);
      if(kind==='typhoon'&&n.cyclone.phase==='eye'){ptype='none';rate=0;ws=.12;cl=.2;}
    }else{
      ptype=fields.precipitation.type;rate=fields.precipitation.rate;temp=fields.temperature_c;
      ws=fields.wind.speed;cl=fields.cloud_cover;hum=fields.humidity;fg=fields.fog;
    }
    var dust=AEROSOL_OF[kind]||['none',0,0],din=DUST_KINDS.indexOf(kind)>=0?dust[1]+dust[2]*intensity:0;
    if(fields&&DUST_KINDS.indexOf(kind)>=0)din=fields.aerosol.density;
    return [ptype,rate,temp,ws,cl,n.p[8],kind==='ashfall'?intensity:0,kind==='mana_storm'?intensity:0,n.dark,hum,fg,din];
  }

  function step(g, v) {
    g=g.slice();v=v.slice();while(g.length<GROUND_NAMES.length)g.push(0);while(v.length<12)v.push(0);
    var wet=g[0],pud=g[1],snow=g[2],hail=g[3],ash=g[4],mana=g[5],glaze=g[6],frost=g[7],rime=g[8],dust=g[9],graupel=g[10];
    var ptype=v[0],rate=v[1],temp=v[2],ws=v[3],cl=v[4],snowb=v[5],ashIn=v[6],manaIn=v[7],dark=v[8],humidity=v[9],fog=v[10],dustIn=v[11];
    var wetting=WET_TYPES.indexOf(ptype)>=0;
    if(wetting){wet=Math.min(1,wet+.08+.5*rate);pud=Math.min(1,pud+.15*rate);}
    else{
      var dry=(.03+.05*clamp01(temp/30)+.04*ws)*(1-.4*cl);if(temp<0)dry*=.3;
      pud=Math.max(0,pud-.6*dry);wet=Math.max(0,wet-dry);
    }
    if(ptype==='snow'&&temp<=1)snow+=.06*rate+.01;
    else if(ptype==='sleet'&&temp<1)snow+=.015*rate;
    if(snow>snowb||temp<=0)snow+=SNOW_RELAX*(snowb-snow);
    if(temp>0&&snow>0){var m=Math.min(snow,.006*temp+(wetting?.02*rate:0));snow-=m;wet=Math.min(1,wet+.4*m);}
    snow=clamp01(snow);
    if(ptype==='hail')hail=Math.min(1,hail+.25*rate);else hail=Math.max(0,hail-(.02+.004*Math.max(temp,0)));
    if(ashIn>0)ash=Math.min(1,ash+.06*ashIn);else ash=Math.max(0,ash-.006*ash-(wetting?.02*rate:0));
    if(manaIn>0)mana=Math.min(1,mana+.08*manaIn);else mana*=1-.012;
    var thaw=.02+.012*Math.max(temp,0);
    if(ptype==='freezing_rain'&&temp<=0)glaze=Math.min(1,glaze+.12*rate);
    else if(temp>0){var melt=Math.min(glaze,thaw);glaze-=melt;wet=Math.min(1,wet+.4*melt);}
    else glaze=Math.max(0,glaze-.003);
    if(ptype==='graupel')graupel=Math.min(1,graupel+.15*rate);else graupel=Math.max(0,graupel-thaw);
    if(temp<=0&&dark>.3&&cl<=.3&&ws<=.25&&!wetting)frost=Math.min(1,frost+.08*dark);
    else frost=Math.max(0,frost-(.4*(1-dark)+thaw+.1*rate));
    if(temp<=-2&&fog>=.3&&humidity>=.8)rime=Math.min(1,rime+.1*fog);
    else rime=Math.max(0,rime-thaw-.05*(1-dark));
    if(dustIn>0)dust=Math.min(1,dust+.05*dustIn);else dust=Math.max(0,dust*.94-(wetting?.3*rate:.003));
    return [Math.max(wet,pud),pud,snow,hail,ash,mana,glaze,frost,rime,dust,graupel];
  }

  function ground(c,t,cur,ov){
    cur=cur.slice();while(cur.length<12)cur.push(0);
    function initial(v){var a=new Array(GROUND_NAMES.length).fill(0);a[2]=v[5];return a;}
    var forced=GROUND_KEYS.some(function(k){return has(ov,k);}),g,k,h;
    if(forced){g=initial(cur);for(k=0;k<WINDOW_HOURS+1;k++)g=step(g,cur);return g;}
    var start=Math.floor(t/24)*24-WINDOW_HOURS,end=Math.ceil(t)-1,hit=c.gcache[start];
    if(hit&&hit[0]<=end){h=hit[0];g=hit[1];}else{h=start-1;g=null;}
    while(h<end){h++;var n=natural(c,h),v=core(n.kind,n.intensity,n);if(g===null)g=initial(v);g=step(g,v);}
    memoPut(c.gcache,start,[h,g],32);
    return step(g,cur);
  }

  function timeOf(c, day, hour) { // weather.py _time
    var rs = sunOf(c, day);
    return { hour: hour, day_of_year: mod(c.start + day - 2, 365) + 1, sunrise: rs[0], sunset: rs[1],
      moon_phase: mod((day - 1 + hour / 24) / MOON_PERIOD_DAYS, 1.0) };
  }

  function windDir(c, ts) {
    var base=flowDirection(c);
    if(c.south&&c.lat==null)base=180-base;
    return mod(base+(u(c.hs,7,ts,48,12)-.5)*140,360);
  }

  function derive(c, kind, i, n, ov) { // weather.py _derive
    function pick(name, v) { return has(ov, name) ? ov[name] : fit(kind, name, clamp01(v)); }
    var ts = n.ts;
    var ptype = ptypeOf(kind, n, ov);
    var rate = has(RATE, kind) ? pick('precipitation.rate', RATE[kind] * i) : 0.0;
    var temp = has(ov, 'temperature_c') ? ov.temperature_c : fit(kind, 'temperature_c', n.temp);
    var cl;
    if (has(CLOUD_BAND, kind)) cl = i;
    else if (has(CLOUD_OF, kind)) cl = CLOUD_OF[kind][0] + CLOUD_OF[kind][1] * i;
    else if (kind === 'sandstorm') cl = n.cl * 0.5;
    else if (kind === 'aurora') cl = n.cl;
    else cl = Math.max(n.cl, 0.5);
    cl = pick('cloud_cover', cl);
    var fg;
    if (has(FOG_OF, kind)) fg = FOG_OF[kind][0] + FOG_OF[kind][1] * i;
    else if (kind === 'sandstorm') fg = 0.05;
    else fg = 0.3 * n.lf;
    fg = pick('fog', fg);
    var windy = has(WIND_FLOOR, kind);
    var ws = n.ws;
    if (windy) ws = Math.max(ws, WIND_FLOOR[kind][0] + WIND_FLOOR[kind][1] * i);
    ws = pick('wind.speed', ws);
    var gust = pick('wind.gust', ws * (0.25 + 0.5 * u(c.hs, 9, ts, 6, 2)) + (windy ? 0.3 * i : 0.0));
    var wdir = has(ov, 'wind.dir_deg') ? ov['wind.dir_deg'] : windDir(c, ts);
    var lightning = pick('lightning', kind === 'storm' ? 0.1 + 0.9 * i : 0.0);
    var mist = kind === 'fog' || kind === 'spirit_mist' || kind === 'miasma';
    var hum;
    if (has(RATE, kind)) hum = 0.85 + 0.15 * i;
    else if (mist) hum = 0.9 + 0.1 * i;
    else if (kind === 'sandstorm') hum = 0.15;
    else if (kind === 'ashfall') hum = 0.25 + 0.2 * cl;
    else hum = 0.3 + 0.35 * cl + 0.2 * n.night + 0.3 * n.p[2];
    hum = pick('humidity', hum);
    var vis;
    if (has(RATE, kind)) vis = 1 - VCOST[kind] * i - 0.7 * fg;
    else if (mist) vis = 1 - fg;
    else if (kind === 'sandstorm') vis = 0.45 - 0.4 * i;
    else if (kind === 'ashfall') vis = 0.85 - 0.5 * i - 0.3 * fg;
    else vis = 1 - 0.7 * fg - 0.05 * cl;
    vis = pick('visibility', vis);
    var aBase = kind === 'aurora' ? i : n.ar;
    var aStr = pick('aurora.strength', aBase * (1 - cl));
    var aHue = pick('aurora.hue', aStr * (0.15 + 0.6 * u(c.hs, 12, ts, 10, 3)));
    var mStr = 0.0, mHue = 0.0, mPulse = 0.0;
    if (FANTASY.indexOf(kind) >= 0) {
      mStr = MAGIC_OF[kind][0] + MAGIC_OF[kind][1] * i;
      mHue = MAGIC_HUE[kind][0] + MAGIC_HUE[kind][1] * (u(c.hs, 13, ts, 12, 4) - 0.5);
      mPulse = MAGIC_PULSE[kind][0] + MAGIC_PULSE[kind][1] * i;
    }

    var aerosol=AEROSOL_OF[kind]||['none',0,0], atype=aerosol[0];
    var density=has(ov,'aerosol.density')?ov['aerosol.density']:aerosol[1]+aerosol[2]*i;
    if(atype!=='none')vis=has(ov,'visibility')?ov.visibility:Math.min(vis,1-.9*density);
    var phase='none',category=0;
    if(kind==='typhoon'){
      category=has(ov,'cyclone.category')?ov['cyclone.category']:(n.cyclone.category||2);
      phase=has(ov,'cyclone.phase')?ov['cyclone.phase']:n.cyclone.phase;
      if(phase==='none')phase=i<.4?'outer':'eyewall';
      if(phase==='eye'){
        ws=has(ov,'wind.speed')?ov['wind.speed']:.12;
        gust=has(ov,'wind.gust')?ov['wind.gust']:.08;
        cl=has(ov,'cloud_cover')?ov.cloud_cover:.2;
        rate=has(ov,'precipitation.rate')?ov['precipitation.rate']:(ov['precipitation.type']==='rain'?.1:0);
        ptype=rate>0?'rain':'none';
      }
    }
    var heat=pick('heat',kind==='heatwave'?i:clamp01((temp-30)/15)), recent=false;
    if(RAINBOW_KINDS.indexOf(kind)>=0)recent=kind==='sunshower'||[1,2].some(function(h){return LIQUID_KINDS.indexOf(natural(c,n.t-h).kind)>=0;});
    var tm=timeOf(c,Math.floor(n.t/24)+1,mod(n.t,24));
    var lowSun=Math.min(Math.abs(tm.hour-tm.sunrise),Math.abs(tm.hour-mod(tm.sunset,24)))<3;
    var rainbow=pick('rainbow',recent&&lowSun&&n.dark===0?.7*(1-cl):0);
    return { precipitation: { type: ptype, rate: rate }, cloud_cover: cl, fog: fg,
      wind: { dir_deg: wdir, speed: ws, gust: gust }, lightning: lightning,
      temperature_c: temp, humidity: hum, visibility: vis,
      aurora: { strength: aStr, hue: aHue },
      magic: { strength: pick('magic.strength', mStr), hue: pick('magic.hue', mHue), pulse: pick('magic.pulse', mPulse) },
      aerosol:{type:atype,density:density},heat:heat,rainbow:rainbow,cyclone:{category:category,phase:phase},vortex:pick('vortex',i) };
  }

  // ------------------------------------------------------------ argument checks
  function isNum(v) { return typeof v === 'number' && isFinite(v); }
  function isInt(v) { return typeof v === 'number' && Math.floor(v) === v && isFinite(v); }
  function numIn(name, v, lo, hi) {
    if (!isNum(v)) throw new Error('覆盖字段 ' + name + ' 必须是有限数字');
    if (!(lo <= v && v <= hi)) throw new Error('覆盖字段 ' + name + '=' + v + ' 超出范围 [' + lo + ', ' + hi + ']');
    return v;
  }
  function flatOverrides(overrides){
    if(overrides==null)return {};
    if(typeof overrides!=='object'||Array.isArray(overrides))throw new Error('overrides 必须是字典');
    var flat={};
    Object.keys(overrides).forEach(function(k){
      var v=overrides[k];
      if(k==='kind'){if(KINDS.indexOf(v)<0)throw new Error('未知 kind');flat.kind=v;}
      else if(has(OVERRIDE_FIELDS,k))flat[k]=numIn(k,v,OVERRIDE_FIELDS[k][0],OVERRIDE_FIELDS[k][1]);
      else if(has(OVERRIDE_NESTED,k)){
        if(v==null||typeof v!=='object'||Array.isArray(v))throw new Error(k+' 必须是字典');
        Object.keys(v).forEach(function(sk){
          if(!has(OVERRIDE_NESTED[k],sk))throw new Error('不支持字段 '+k+'.'+sk);
          var r=OVERRIDE_NESTED[k][sk],name=k+'.'+sk;
          if(typeof r[0]==='string'){if(typeof v[sk]!=='string'||r.indexOf(v[sk])<0)throw new Error('未知 '+name);flat[name]=v[sk];}
          else{flat[name]=numIn(name,v[sk],r[0],r[1]);if(k==='cyclone'&&sk==='category'&&!isInt(v[sk]))throw new Error('cyclone.category 必须是整数');}
        });
      }else throw new Error('不支持字段 '+k);
    });return flat;
  }
  var MAX_SEED = Math.pow(2, 50); // weather.py MAX_SEED
  function context(seed,climate,season,lat,lon,calendar,fantasy,elevation,coastDistance){
    if(!isInt(seed)||Math.abs(seed)>MAX_SEED)throw new Error('seed 必须是安全整数');
    if(typeof climate!=='string'||!has(CLIMATES,climate))throw new Error('未知 climate');
    if(season!=null&&SEASONS.indexOf(season)<0)throw new Error('未知 season');
    if(lat!=null&&(!isNum(lat)||Math.abs(lat)>90))throw new Error('lat 越界');
    if(lon!=null&&(!isNum(lon)||Math.abs(lon)>180))throw new Error('lon 越界');
    if(elevation!=null&&(!isNum(elevation)||elevation<-500||elevation>9000))throw new Error('elevation 越界');
    if(coastDistance!=null&&(!isNum(coastDistance)||coastDistance<0||coastDistance>40075))throw new Error('coast_distance_km 越界');
    if(fantasy==null)fantasy=[];
    if(!Array.isArray(fantasy)||fantasy.some(function(f){return FANTASY.indexOf(f)<0;}))throw new Error('未知 fantasy');
    var allowed=FANTASY.filter(function(f){return fantasy.indexOf(f)>=0;});
    lon=lon===180?-180:lon;
    var cal=calendar==null?null:checkCalendar(calendar);
    var id=JSON.stringify([seed,climate,season||null,lat==null?null:lat,lon==null?null:lon,cal,allowed,elevation==null?null:elevation,coastDistance==null?null:coastDistance]);
    var c=CONTEXTS.get(id);
    if(c){CONTEXTS.delete(id);CONTEXTS.set(id,c);return c;}
    c=new Ctx(seed,climate,season==null?null:season,lat==null?null:lat,lon==null?null:lon,cal,allowed,elevation,coastDistance);
    CONTEXTS.set(id,c);if(CONTEXTS.size>MAX_CONTEXTS)CONTEXTS.delete(CONTEXTS.keys().next().value);
    return c;
  }
  function checkTime(day, hour) {
    if (!isInt(day) || Math.abs(day) > 1000000) throw new Error('day 必须是 |day| ≤ 1000000 的整数（第 1 天 = 日历起始日）');
    if (!isNum(hour) || hour < 0 || hour >= 24) throw new Error('hour 必须在 [0, 24)');
  }

  function state(c,day,hour,ov){
    var t=(day-1)*24+hour,n=natural(c,t),kind=chooseKind(c,n,ov),i=intensityOf(c,t,kind,n,ov),f=derive(c,kind,i,n,ov);
    var cur=groundInput(kind,i,n,f),g=ground(c,t,cur,ov),gr={};
    GROUND_NAMES.forEach(function(k,j){gr[k]=has(ov,'ground.'+k)?ov['ground.'+k]:g[j];});
    return {seed:c.seed,time:timeOf(c,day,hour),kind:kind,intensity:i,precipitation:f.precipitation,
      cloud_cover:f.cloud_cover,fog:f.fog,wind:f.wind,lightning:f.lightning,temperature_c:f.temperature_c,
      humidity:f.humidity,visibility:f.visibility,ground:gr,aurora:f.aurora,magic:f.magic,
      season:c.season||n.season,climate:c.climate,aerosol:f.aerosol,rainbow:f.rainbow,heat:f.heat,cyclone:f.cyclone,vortex:f.vortex};
  }

  function ctxOf(seed,climate,o){return context(seed,climate,o.season,o.lat,o.lon,o.calendar,o.fantasy,o.elevation,o.coast_distance_km);}
  // opts: { season, overrides, fantasy, lon, lat, elevation, calendar }（与 Python 关键字参数同名）
  function weatherAt(seed, day, hour, climate, opts) {
    var o = opts || {};
    var c = ctxOf(seed, climate, o);
    checkTime(day, hour);
    return state(c, day, hour, flatOverrides(o.overrides));
  }
  // opts 另可带 step（小时，默认 1）
  function forecast(seed, startDay, startHour, hours, climate, opts) {
    var o = opts || {};
    var c = ctxOf(seed, climate, o);
    checkTime(startDay, startHour);
    if (!isInt(hours) || hours < 0 || hours > 1440) throw new Error('hours 必须是 0..1440 的整数');
    var step = o.step == null ? 1 : o.step;
    if (!isNum(step) || !(step > 0 && step <= 24)) throw new Error('step 必须在 (0, 24]');
    var ov = flatOverrides(o.overrides), out = [];
    for (var k = 0; k < hours; k++) {
      var h = startHour + k * step;
      out.push(state(c, startDay + Math.floor(h / 24), mod(h, 24), ov));
    }
    return out;
  }

  var CELL_KEYS = ['id', 'lon', 'lat', 'climate', 'elevation', 'coast_distance_km'];
  // cells: [{id, lon, lat, climate, elevation?}]；opts: { calendar, fantasy, season }（weather.py region_weather）
  function regionWeather(seed, cells, day, hour, opts) {
    var o = opts || {};
    if (!Array.isArray(cells)) throw new Error('cells 必须是列表');
    if(cells.length>4096)throw new Error('regionWeather 每批最多 4096 格');
    checkTime(day,hour);context(seed,'temperate',o.season,null,null,o.calendar,o.fantasy);
    var seen = {}, out = [];
    for (var j = 0; j < cells.length; j++) {
      var cell = cells[j];
      if (cell == null || typeof cell !== 'object' || Array.isArray(cell)) throw new Error('cells 的每一项必须是字典');
      var extra = Object.keys(cell).filter(function (k) { return CELL_KEYS.indexOf(k) < 0; }).sort();
      if (extra.length) throw new Error('cell 不支持字段 ' + extra.join(', '));
      var req = ['id', 'lon', 'lat', 'climate'];
      for (var r = 0; r < req.length; r++) if (!has(cell, req[r])) throw new Error('cell 缺少字段 ' + req[r]);
      var cid = cell.id, sid = typeof cid + ':' + cid;
      if (!(typeof cid === 'string' || isInt(cid)) || has(seen, sid))
        throw new Error('cell id ' + JSON.stringify(cid) + ' 必须是唯一的字符串或整数');
      seen[sid] = true;
      if (cell.lon == null || cell.lat == null) throw new Error('cell 的 lon / lat 不能为空');
      out.push(weatherAt(seed, day, hour, cell.climate, { season: o.season, fantasy: o.fantasy, lon: cell.lon,
        lat: cell.lat, elevation: cell.elevation, coast_distance_km:cell.coast_distance_km, calendar: o.calendar }));
    }
    return out;
  }

  function climateByLat(lat, water) {
    var a = Math.abs(lat);
    if (a >= 66) return 'polar';
    if (a >= 50) return water ? 'maritime' : 'continental';
    if (a >= 35) return water ? 'maritime' : 'temperate';
    if (a >= 23.5) return 'subtropical_monsoon';
    return 'tropical';
  }
  function climateFor(biome, lat) {
    if (typeof biome === 'number') {
      if (!isInt(biome) || biome < 0 || biome >= BIOMES.length) throw new Error('群系下标 ' + biome + ' 超出 0..' + (BIOMES.length - 1));
      biome = BIOMES[biome];
    }
    if (biome != null && !has(BIOME_CLIMATE, biome)) throw new Error('未知群系 ' + JSON.stringify(biome));
    if (lat != null && (!isNum(lat) || Math.abs(lat) > 90)) throw new Error('lat 必须是 [-90, 90] 内的数字');
    var fixed = biome != null ? BIOME_CLIMATE[biome] : null;
    if (fixed) return fixed;
    if (lat == null) return 'temperate';
    return climateByLat(lat, biome === '海洋' || biome === '湖泊');
  }

  var STATE_KEYS = ['seed', 'time', 'kind', 'intensity', 'precipitation', 'cloud_cover', 'fog', 'wind', 'lightning',
    'temperature_c', 'humidity', 'visibility', 'ground', 'aurora', 'magic', 'season', 'climate','aerosol','rainbow','heat','cyclone','vortex'];
  var UNIT = ['intensity', 'cloud_cover', 'fog', 'lightning', 'humidity', 'visibility','rainbow','heat','vortex'];
  function validateState(s) {
    function num(name, v, lo, hi) {
      if (!isNum(v) || v < lo || v > hi) throw new Error(name + '=' + JSON.stringify(v) + ' 不在 [' + lo + ', ' + hi + ']');
    }
    function keys(name, d, want) {
      if (d == null || typeof d !== 'object') throw new Error(name + ' 字段应为 ' + want.slice().sort().join(','));
      var got = Object.keys(d).sort().join(','), exp = want.slice().sort().join(',');
      if (got !== exp) throw new Error(name + ' 字段应为 ' + exp);
    }
    keys('state', s, STATE_KEYS);
    if (!isInt(s.seed)) throw new Error('seed 必须是整数');
    var tm = s.time;
    keys('time', tm, ['hour', 'day_of_year', 'sunrise', 'sunset', 'moon_phase']);
    num('time.hour', tm.hour, 0, 24); num('time.sunrise', tm.sunrise, 0, 24);
    num('time.sunset', tm.sunset, 0, 48); num('time.moon_phase', tm.moon_phase, 0, 1);
    if (!isInt(tm.day_of_year) || tm.day_of_year < 1 || tm.day_of_year > 365) throw new Error('time.day_of_year 必须是 1..365 的整数');
    if (KINDS.indexOf(s.kind) < 0) throw new Error('未知 kind ' + s.kind);
    if (SEASONS.indexOf(s.season) < 0) throw new Error('未知 season ' + s.season);
    if (!has(CLIMATES, s.climate)) throw new Error('未知 climate ' + s.climate);
    for (var j = 0; j < UNIT.length; j++) num(UNIT[j], s[UNIT[j]], 0, 1);
    num('temperature_c', s.temperature_c, -80, 60);
    keys('precipitation', s.precipitation, ['type', 'rate']);
    if (PRECIP_TYPES.indexOf(s.precipitation.type) < 0) throw new Error('未知降水类型 ' + s.precipitation.type);
    num('precipitation.rate', s.precipitation.rate, 0, 1);
    if ((s.precipitation.type === 'none') !== (s.precipitation.rate === 0)) throw new Error('precipitation.type 为 none 当且仅当 rate 为 0');
    keys('wind', s.wind, ['dir_deg', 'speed', 'gust']);
    num('wind.dir_deg', s.wind.dir_deg, 0, 360); num('wind.speed', s.wind.speed, 0, 1); num('wind.gust', s.wind.gust, 0, 1);
    keys('ground', s.ground, GROUND_NAMES);
    for (var gk = 0; gk < GROUND_NAMES.length; gk++) num('ground.' + GROUND_NAMES[gk], s.ground[GROUND_NAMES[gk]], 0, 1);
    keys('aurora', s.aurora, ['strength', 'hue']);
    keys('magic', s.magic, ['strength', 'hue', 'pulse']);
    ['aurora', 'magic'].forEach(function (name) {
      for (var f in s[name]) num(name + '.' + f, s[name][f], 0, 1);
    });

    keys('aerosol',s.aerosol,['type','density']);num('aerosol.density',s.aerosol.density,0,1);
    if(AEROSOL_TYPES.indexOf(s.aerosol.type)<0)throw new Error('未知 aerosol.type');
    keys('cyclone',s.cyclone,['category','phase']);
    var cat=s.cyclone.category,phase=s.cyclone.phase;
    if(!isInt(cat)||CYCLONE_PHASES.indexOf(phase)<0||(phase==='none'?cat!==0:cat<1||cat>5))throw new Error('cyclone 等级与阶段不一致');
    var subset={};Object.keys(s).forEach(function(k){if((has(OVERRIDE_FIELDS,k)||has(OVERRIDE_NESTED,k))&&(k!=='cyclone'||phase!=='none'))subset[k]=s[k];});
    var why=conflict(s.kind,flatOverrides(subset));if(why)throw new Error(why);
    if(s.kind==='typhoon'&&phase==='none')throw new Error('台风必须有阶段');
    return s;
  }

  var api = { clearCache:clearCache, cacheInfo:cacheInfo, weatherAt: weatherAt, forecast: forecast, regionWeather: regionWeather, climateFor: climateFor,
    validateState: validateState, KINDS: KINDS.slice(), NATURAL: NATURAL.slice(), FANTASY: FANTASY.slice(),
    GROUND_NAMES: GROUND_NAMES.slice(), SEASONS: SEASONS.slice(), CLIMATES: CLIMATE_NAMES.slice(), BIOMES: BIOMES.slice(),
    WINDOW_HOURS: WINDOW_HOURS, _noise: { h32: h32, sig: sig, cdf: cdf } };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.WeatherGen = api;
})(typeof window !== 'undefined' ? window : this);
