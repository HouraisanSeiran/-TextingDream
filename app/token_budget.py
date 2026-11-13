"""Output ceilings in model tokens; these are not input or context-window sizes."""

TINY_OUTPUT = 256
SHORT_OUTPUT = 1024
MEDIUM_OUTPUT = 2048
STANDARD_OUTPUT = 4096
LONG_OUTPUT = 8192
MAX_OUTPUT = 65536
DEFAULT_OUTPUT = LONG_OUTPUT

TASK_OUTPUT_TOKENS = {
    'connection_test': TINY_OUTPUT,
    'intent': TINY_OUTPUT,
    'surface': SHORT_OUTPUT,
    'player_reply': SHORT_OUTPUT,
    'polish': LONG_OUTPUT,
    'inner': STANDARD_OUTPUT,
    'development': STANDARD_OUTPUT,
    'ai_draft_element': STANDARD_OUTPUT,
    'ai_draft_npc': STANDARD_OUTPUT,
    'background_select': MEDIUM_OUTPUT,
    'background_profiles': STANDARD_OUTPUT,
    'background_environment': LONG_OUTPUT,
    'background_elements': LONG_OUTPUT,
    'background_history': LONG_OUTPUT,
    'background_polity': STANDARD_OUTPUT,
    'background_continents': STANDARD_OUTPUT,
    'background_overview': STANDARD_OUTPUT,
    'world_package_history': LONG_OUTPUT,
    'world_package_politics': LONG_OUTPUT,
    'world_package_setting': LONG_OUTPUT,
}


def output_tokens(scope, requested=None, fallback=DEFAULT_OUTPUT):
    """Explicit request > task default > legacy API fallback; never trim output text."""
    if requested is not None:
        value = requested
    elif scope in TASK_OUTPUT_TOKENS:
        value = TASK_OUTPUT_TOKENS[scope]
    elif scope.startswith('generator_'):
        value = STANDARD_OUTPUT
    elif scope.startswith('world_stage_'):
        value = LONG_OUTPUT
    else:
        value = fallback
    if type(value) is not int or not 1 <= value <= MAX_OUTPUT:
        raise ValueError(f'输出 token 上限必须为 1 至 {MAX_OUTPUT} 的整数')
    return value
