"""Explicit, audience-scoped engine facts; no inferred calendar or scenery."""


def state_anchor(session, place, chapter, characters):
    hour = session['time']
    return {
        'source': '本地引擎已确认；无需重新计算或推测',
        'phase': '当前状态快照；若有本轮行动，已包含其裁定和耗时',
        'clock': {
            'game_day': hour // 24 + 1,
            'local_time': f'{hour % 24:02d}:00',
            'precision': '游戏整点，24小时制',
            'calendar': '游戏第几天，不对应历史年月日；没有配置时区换算',
        },
        'location_id': place['id'],
        'location': place['name'],
        'chapter_title': chapter,
        'chapter_semantics': '章节归档名称，可能沿用旧标题；不是此刻时间或位置',
        'co_located_characters': [{'id': c['id'], 'name': c['name']} for c in characters],
        'presence_scope': '仅确认同一登记地点，不保证近在眼前、参与交谈或听见输入；听众以listeners为准',
        'unspecified': '房间、天气、日出日落未由时钟确认，不根据整点推算',
    }
