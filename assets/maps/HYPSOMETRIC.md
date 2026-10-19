# 分层设色地形底图

展示规则：按海拔分段填色，不按森林、沙漠等地貌类型填色。陆地各档区间左闭右开，最高档为6000米及以上；海洋按水深分档。陆地下凹低地使用单独绿色，与海洋区分。

数据：GMT IGPP Earth Relief `earth_relief_10m_g.grd`。官方说明指出低分辨率产品由 SRTM15+V2.7 滤波降采样而来（Tozer et al., 2019）。网格间隔10角分，适合全球测试图，不用于精细测绘、坡度计算或现实边界认定。

- 高程数据与引用说明：https://www.generic-mapping-tools.org/remote-datasets/earth-relief.html
- 数据门户：https://www.generic-mapping-tools.org/remote-datasets/
- 原始数据论文：https://doi.org/10.1029/2019EA000658
- 海陆遮罩：项目原有 Natural Earth 1:50m land，公共领域。
- 制图脚本：tools/build_hypsometric_map.py；输出及来源校验信息：world-hypsometric.png、world-hypsometric-source.json。

按网格的scale/offset还原米数，再重投影到等距经纬网、按固定色阶着色。无阴影叠色，保证同一高度档颜色一致；海陆使用独立遮罩。

该图是现实地形测试底图。故事包中明确提供海拔的区域使用同一色阶覆盖；只有地点海拔时仅显示色点，不凭空扩成山脉；没有海拔的区域仅显示虚线边界。矿产、沃土、人口、水系、政区等图层继续独立显示。没有修改故事包数据或生成规则。

用户提供的百度百科页面返回安全验证，未声称已读取该页正文。本次按分层设色地图的海拔分段着色原理实现，不把参考链接添加到游戏操作界面。
