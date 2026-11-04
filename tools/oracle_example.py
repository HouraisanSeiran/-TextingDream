"""User-authored oracle example; build only, never install a package."""
from app import attributes

WEAKNESS = '阿喀琉斯的弱点是脚后跟。'
COOPERATION = '帕里斯愿意在收到决斗时间和地点后合作射击。'
MISDIRECTION = '女祭司称忒提斯回应：赤手空拳按顺序打上半身108穴。'


def build_example():
    def information(text, confirmed=False):
        return {'op': 'information', 'text': text,
                'known_by': ['player'], 'confirmed': confirmed}

    story = {
        'id': 'achilles_oracle_example', 'title': '向阿波罗献贡',
        'premise': '用户原创占卜场景，不作神话考据。',
        'worldview': {'premise': '用户原创占卜场景'},
        'character_package_id': 'oracle_cast',
        'locations': [{'id': 'temple', 'name': '神庙', 'description': '神庙',
                       'neighbors': [], 'scenes': []}],
        'items': [],
        'knowledge': [{'id': 'oracle_author', 'visibility': 'author',
                       'keywords': ['阿喀琉斯'],
                       'content': WEAKNESS + '108穴说法是本场景误导，不是作者事实。'}],
        'mechanics': {
            'attributes': attributes.specification(),
            'checks': {'version': 2, 'tier_mode': 'margin_four'},
            'local': {'turn_hours': 0, 'travel_hours': 1, 'resources': [
                {'id': 'offering', 'name': '贡品', 'unit': '份',
                 'initial': 3, 'maximum': 100}]}},
        'events': [{
            'id': 'oracle', 'title': '献贡询问', 'location_id': 'temple',
            'participants': ['player', 'priestess'], 'player_enters': True,
            'player_goal': '向阿波罗询问', 'next_events': [],
            'entry_flags': {}, 'exit_flag': 'oracle_done', 'max_turns': 10,
            'actions': [
                {'id': 'ask', 'label': '献贡向阿波罗询问', 'ends_event': False,
                 'costs': {'offering': 1},
                 'check': {'attribute': 'wisdom', 'dc': 15,
                           'tiers': {
                               'critical': {'text': WEAKNESS + COOPERATION,
                                            'effects': [information(WEAKNESS, True),
                                                        information(COOPERATION),
                                                        {'op': 'flag', 'id': 'paris_contact_lead',
                                                         'value': True}]},
                               'success': {'text': WEAKNESS,
                                           'effects': [information(WEAKNESS, True)]},
                               'failure': {'text': '拒绝回答。', 'effects': []},
                               'disaster': {'text': MISDIRECTION,
                                            'effects': [information(MISDIRECTION)]}}}},
                {'id': 'leave', 'label': '离开神庙', 'ends_event': True,
                 'success_text': '离开神庙。', 'effects': []}]}],
    }
    characters = {'id': 'oracle_cast', 'title': '占卜人物', 'characters': [
        {'id': 'player', 'name': '我', 'public_name': '我', 'role': '主角',
         'location_id': 'temple', 'personality': {}, 'state': {},
         'attributes': {axis: 50 for axis in attributes.AXES}},
        {'id': 'priestess', 'name': '女祭司', 'public_name': '女祭司', 'role': '次要角色',
         'location_id': 'temple', 'personality': {}, 'state': {},
         'attributes': {axis: 50 for axis in attributes.AXES}}]}
    return {'story': story, 'characters': characters}
