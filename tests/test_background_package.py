"""Background workflow invariants against disposable maps, libraries and model doubles."""
import asyncio
from copy import deepcopy
import json

import pytest

from app import encyclopedia as enc
from app import background_package as background_module
from app.ai_drafts import DraftRejected
from app.background_package import BackgroundPackages, read_background
from app.prompts import stable_json
from app.service import Service
from app.storage import Store
from tests.test_background_geography import FrozenBundle
from tests.test_world_package_pipeline import SETTING, el


CONFIG = {'seed': 2, 'start_year': 0, 'end_year': 2, 'block_cells': 4,
          'min_land_cells': 1, 'max_polities': 2, 'found_period': 1,
          'min_capital_hops': 1, 'war_per_mille': 0}


def run(coro):
    return asyncio.run(coro)


class Registry:
    def __init__(self):
        self.bundle = FrozenBundle()

    def get(self, identity):
        assert identity == self.bundle.id
        self.bundle.check_unchanged()
        return self.bundle


@pytest.fixture
def factory(tmp_path):
    def create(count=9, large=False, budget=18000):
        database = tmp_path / 'encyclopedia.sqlite3'
        elements = [el('lore_%02d' % index, 'Adopted %02d' % index,
                       ['kind:race', 'genre:western_fantasy']) for index in range(count)]
        for index, row in enumerate(elements):
            row['details']['definition'] = ('payload_marker_%02d ' % index) + 'x' * (17000 if large else 1600)
        enc.import_document(database, {'schema_version': 1, 'status': 'candidate', 'group': 'fixture',
                                       'sources': [{'id': 's1', 'title': 'Fixture', 'access': 'read'}],
                                       'elements': elements})
        service = Service(Store(tmp_path / 'state.sqlite3'), tmp_path)
        service.elements.configure(database, allowed_roots=[str(tmp_path)])
        service.provider.configure({'offline': True})
        service.store.put('settings', 'preferences', {'context_chars': budget})
        pipe = BackgroundPackages(service, Registry())
        traces = []
        service.provider.offline_trace = lambda scope, context, output: traces.append(
            (scope, deepcopy(context), deepcopy(output)))
        draft = pipe.propose('fixture-world', SETTING, title='Background', config=CONFIG, year=1)
        return pipe, draft, traces, database
    return create


def simulated(pipe, draft):
    refs = [row['ref'] for row in draft['candidates']['recommended']]
    selected = pipe.select(draft['id'], refs, draft['revision'])
    return pipe.simulate(draft['id'], selected['revision'])


def generated(pipe, draft):
    draft = simulated(pipe, draft)
    return run(pipe.generate(draft['id'], draft['revision']))


def test_all_64_adopted_payloads_are_budgeted_and_covered(factory):
    pipe, draft, traces, _ = factory(count=64)
    draft = generated(pipe, draft)
    element_calls = [context for scope, context, _ in traces if scope == 'background_elements']
    assert len(element_calls) > 1
    seen = set()
    for context in element_calls:
        for row in context['elements']:
            seen.add(row['ref'])
            assert 'payload_marker_' in stable_json(row)
    assert seen == set(draft['selection']['refs'])
    assert {ref for row in draft['content']['knowledge'] for ref in row['element_refs']} == seen
    for scope, context, _ in traces:
        assert len(stable_json(context)) < 18000, scope
    assert any(scope == 'background_history' for scope, _, _ in traces)
    assert draft['content']['history_sections'][0]['event_facts']
    assert len([row for row in draft['content']['knowledge'] if row['element_refs']]) == 64
    assert any(scope == 'background_environment' for scope, _, _ in traces)
    physical = [row for scope, context, _ in traces if scope == 'background_environment'
                for row in context['fields']]
    assert {row['group'] for row in physical} == set(draft['geography']['groups'])
    climate = next(row for row in physical if row['group'] == 'climate')
    assert [row['month'] for row in climate['evidence']['statistics']] == list(range(1, 13))
    native = [row for scope, context, _ in traces if scope == 'background_polity'
              for row in context['knowledge'] if 'evidence' in row]
    assert any(row['geography_refs'] == ['terrain.status'] for row in native)


def test_oversized_payload_is_losslessly_fragmented(factory):
    pipe, draft, traces, _ = factory(count=1, large=True, budget=9000)
    draft = generated(pipe, draft)
    inputs = [row for scope, context, _ in traces if scope == 'background_elements'
              for row in context['elements']]
    assert len(inputs) > 1
    assert [row['part'] for row in inputs] == list(range(1, len(inputs) + 1))
    original = draft['element_manifest']['elements'][0]
    reconstructed = ''.join(row['payload']['source_json_fragment'] for row in inputs)
    assert json.loads(reconstructed) == {'payload': original['payload'],
                                         'adaptation': original.get('adaptation', {})}


def test_64_kingdoms_and_many_landmasses_use_bounded_contexts(factory):
    pipe, draft, traces, _ = factory(count=1)
    draft = simulated(pipe, draft)
    template = draft['simulation']['kingdoms'][0]
    draft['simulation']['kingdoms'] = [dict(deepcopy(template), id='kingdom-%d' % index,
                                          polity_id=index, name='Kingdom %d' % index)
                                        for index in range(64)]
    landmass = draft['simulation']['landmasses'][0]
    draft['simulation']['landmasses'] = [dict(deepcopy(landmass), id='landmass-%d' % index,
                                            name='Landmass %d' % index) for index in range(1000)]
    pipe.service.store.put('world_package_draft', draft['id'], draft)
    draft = run(pipe.generate(draft['id'], draft['revision']))
    assert len(draft['content']['polities']) == 64
    assert len(draft['content']['continents']) == 1000
    assert len([scope for scope, _, _ in traces if scope == 'background_continents']) > 1
    overview = next(context for scope, context, _ in traces if scope == 'background_overview')
    assert len(overview['polities']) == 64 and overview['landmass_count'] == 1000
    assert 'continents' not in overview
    assert all(len(stable_json(context)) < 18000 for _, context, _ in traces)


class Online:
    def __init__(self, respond):
        self.respond = respond
        self.calls = []

    def config(self):
        return {'offline': False, 'thinking_mode': 'disabled'}

    async def complete(self, system, context, **kwargs):
        self.calls.append((kwargs['scope'], deepcopy(context)))
        return self.respond(kwargs['scope'], context), {'prompt_tokens': 1}


@pytest.mark.parametrize('field,value', [('year', 9999), ('kind', 'invented-war'), ('polity_a', 999)])
def test_invalid_history_fact_fails_once_and_preserves_draft(factory, field, value):
    pipe, draft, _, _ = factory(count=1)
    draft = simulated(pipe, draft)

    def respond(scope, context):
        if scope == 'background_environment':
            return {'summary': 'Frozen natural conditions.',
                    'knowledge': [{'id': 'environment', 'title': 'Environment', 'content': 'Frozen data.',
                                    'element_refs': [], 'geography_refs': [row['ref'] for row in context['fields']]}]}
        if scope == 'background_elements':
            return {'knowledge': [{'id': 'k', 'title': 'Lore', 'content': 'Adopted lore.',
                                    'element_refs': [context['elements'][0]['ref']]}]}
        assert scope == 'background_history'
        event = context['events'][0]
        fact = pipe._event_fact(event)
        fact[field] = value
        return {'history_sections': [{'title': 'Invalid', 'text': 'Wrong date.',
                 'event_ids': [event['id']], 'event_facts': [fact]}]}

    provider = pipe.service.provider = Online(respond)
    with pytest.raises(DraftRejected, match='年份'):
        run(pipe.generate(draft['id'], draft['revision']))
    assert [scope for scope, _ in provider.calls].count('background_history') == 1
    assert pipe.get(draft['id']) == draft


def test_auto_selection_estimates_profile_from_adopted_evidence(factory):
    pipe, draft, _, _ = factory(count=2)

    def respond(scope, context):
        if scope == 'background_select':
            return {'refs': [row['ref'] for row in context['candidates']]}
        assert scope == 'background_profiles'
        weights = dict(context['default_weights'], highland=-500)
        return {'profiles': [{'id': 'mountain', 'source_refs': [row['ref'] for row in context['elements']],
                              'rationale': 'Author-facing design estimate.', 'weights': weights}]}

    pipe.service.provider = Online(respond)
    selected = run(pipe.auto_select(draft['id'], draft['revision']))
    profile = selected['polity_preferences'][0]
    assert profile['source']['design_estimate'] is True
    assert set(profile['source']['source_refs']) == set(selected['selection']['refs'])
    assert profile['weights']['highland'] == -500
    result = pipe.simulate(draft['id'], selected['revision'])
    assert result['simulation']['profiles'][0]['weights']['highland'] == -500
    assert result['simulation']['selected_elements'][0]['payload_hash']


def test_invalid_profile_does_not_commit_selection_or_retry(factory):
    pipe, draft, _, _ = factory(count=1)

    def respond(scope, context):
        if scope == 'background_select':
            return {'refs': [row['ref'] for row in context['candidates']]}
        return {'profiles': [{'id': 'bad', 'source_refs': ['unknown/ref'],
                              'rationale': 'bad', 'weights': context['default_weights']}]}

    provider = pipe.service.provider = Online(respond)
    with pytest.raises(DraftRejected):
        run(pipe.auto_select(draft['id'], draft['revision']))
    assert pipe.get(draft['id']) == draft
    assert len(provider.calls) == 2


def test_configure_during_generation_wins_cas_without_partial_content(factory):
    pipe, draft, _, _ = factory(count=1)
    draft = simulated(pipe, draft)
    changed = []

    def trace(scope, context, output):
        if not changed:
            changed.append(pipe.configure(draft['id'], year=0, expected_revision=draft['revision']))

    pipe.service.provider.offline_trace = trace
    with pytest.raises(ValueError, match='草稿已变化'):
        run(pipe.generate(draft['id'], draft['revision']))
    assert pipe.get(draft['id']) == changed[0]
    assert changed[0]['content'] is None and changed[0]['simulation'] is None
    assert changed[0]['element_manifest'] == draft['element_manifest']


def test_freshness_never_requeries_native_arrays(factory):
    pipe, draft, _, _ = factory(count=1)
    bundle = pipe.registry.bundle
    calls = len(bundle.calls)
    assert not pipe.freshness(draft['id'])['stale']
    assert len(bundle.calls) == calls
    bundle.record['sources']['climate']['identity'] = 'updated'
    assert pipe.freshness(draft['id'])['stale']
    assert len(bundle.calls) == calls


def test_polity_background_receives_selected_year_history_and_people(factory):
    pipe, draft, traces, _ = factory(count=1)
    draft = generated(pipe, draft)
    inputs = [row for scope, context, _ in traces if scope == 'background_polity'
              for row in context['knowledge']]
    actual_events = [row['event'] for row in inputs if row.get('kind') == 'simulation_event']
    assert actual_events
    assert all(row['year'] <= draft['year'] for row in actual_events)
    actual_people = [row['record'] for row in inputs if row.get('kind') == 'simulation_people']
    assert actual_people == draft['simulation']['chronicle']['people']
    assert actual_people
    assert any(row.get('kind') == 'simulation_polity' and row['record']['alive'] for row in inputs)


def test_immutable_publish_approval_town_context_and_revise(factory):
    pipe, draft, _, database = factory(count=1)
    draft = generated(pipe, draft)
    polity = draft['simulation']['kingdoms'][0]
    content = deepcopy(draft['content'])
    content['major_history_proposals'] = [
        {'id': 'proposal-a', 'year': 0, 'text': 'Author addition.', 'polity_ids': [polity['id']]},
        {'id': 'proposal-b', 'year': 1, 'text': 'Unapproved addition.', 'polity_ids': [polity['id']]}]
    draft = pipe.edit(draft['id'], content, draft['revision'], ['proposal-a'])
    pointer = pipe.service.store.get('pointer', 'package')
    draft = pipe.confirm(draft['id'], draft['revision'])
    version_id = draft['published']['version_id']
    doc = pipe.get_version(version_id)
    assert [row['id'] for row in doc['approved_history']] == ['proposal-a']
    assert [row['id'] for row in doc['unapproved_history']] == ['proposal-b']
    assert pipe.service.store.get('pointer', 'package') == pointer
    folder = pipe.service.runtime.library / doc['folder']
    assert not (folder / 'story.json').exists()
    assert not (folder / 'characters.json').exists()
    context = pipe.town_context(version_id, polity['polity_id'])
    assert context['polity']['geometry'] == polity['geometry']
    assert context['historical_constraints']['capital_region_id'] == polity['capital_region_id']
    assert not context['settlements_generated'] and not context['roads_generated']
    pipe.registry.bundle.changed = True
    database.unlink()
    assert read_background(folder) == doc
    revised = pipe.revise(version_id)
    assert revised['parent_version'] == version_id and revised['id'] != draft['id']
    assert revised['world_id'] == doc['id']
    assert revised['content']['major_history_proposals'] == content['major_history_proposals']
    assert pipe.get_version(version_id) == doc
    pipe.registry.bundle.changed = False
    revision_two = pipe.confirm(revised['id'], revised['revision'])
    version_two = pipe.get_version(revision_two['published']['version_id'])
    assert version_two['version_id'] != version_id and version_two['id'] == doc['id']
    assert version_two['parent_version'] == version_id
    assert pipe.get_version(version_id) == doc
    path = folder / 'background.json'
    tampered = json.loads(path.read_text(encoding='utf-8'))
    tampered['title'] = 'Tampered'
    path.write_text(json.dumps(tampered), encoding='utf-8')
    with pytest.raises(ValueError, match='哈希'):
        pipe.get_version(version_id)


def test_stale_source_refuses_publication(factory):
    pipe, draft, _, _ = factory(count=1)
    draft = generated(pipe, draft)
    pipe.registry.bundle.record['sources']['terrain']['identity'] = 'new-terrain'
    with pytest.raises(ValueError, match='地理来源已变化'):
        pipe.confirm(draft['id'], draft['revision'])
    assert pipe.get(draft['id']) == draft
    assert pipe.list_versions() == []


def test_history_keeps_extinct_polity_and_checks_cited_date(factory):
    pipe, draft, _, _ = factory(count=1)
    draft = generated(pipe, draft)
    simulation = deepcopy(draft['simulation'])
    simulation['chronicle']['snapshots'][0]['polities'].append(
        {'id': 99, 'name': 'Past kingdom', 'alive': False, 'founded': 0})
    draft['simulation'] = simulation
    content = deepcopy(draft['content'])
    content['major_history_proposals'] = [{'id': 'historic', 'year': 0, 'text': 'Past reference.',
                                          'polity_ids': ['kingdom-99']}]
    assert pipe._validate_content(draft, content) == []
    content['history_sections'][0]['text'] = '9999年发生战争。'
    assert any('年份' in error for error in pipe._validate_content(draft, content))


def test_all_background_sections_reject_unadopted_structured_refs(factory):
    pipe, draft, _, _ = factory(count=1)
    draft = generated(pipe, draft)
    for key in ('continents', 'polities', 'history_sections', 'knowledge'):
        content = deepcopy(draft['content'])
        content[key][0]['element_refs'] = ['not/adopted']
        with pytest.raises(DraftRejected, match='未采用'):
            pipe.edit(draft['id'], content, draft['revision'])
        assert pipe.get(draft['id']) == draft


def test_narrative_polity_cannot_shadow_fixed_simulation_facts(factory):
    pipe, draft, _, _ = factory(count=1)
    draft = generated(pipe, draft)
    for field in ('founded', 'ended', 'alive', 'capital_region_id', 'monarch_id', 'geometry'):
        content = deepcopy(draft['content'])
        content['polities'][0][field] = 'invented'
        with pytest.raises(DraftRejected):
            pipe.edit(draft['id'], content, draft['revision'])
        assert pipe.get(draft['id']) == draft


def test_publication_cas_rejects_edit_during_staging(factory, monkeypatch):
    pipe, draft, _, _ = factory(count=1)
    draft = generated(pipe, draft)
    original = background_module.atomic_text
    changed = []

    def write(path, text):
        original(path, text)
        if not changed:
            changed.append(pipe.configure(draft['id'], year=0, expected_revision=draft['revision']))

    monkeypatch.setattr(background_module, 'atomic_text', write)
    with pytest.raises(ValueError, match='草稿已变化'):
        pipe.confirm(draft['id'], draft['revision'])
    assert pipe.get(draft['id']) == changed[0]
    assert pipe.list_versions() == []
    assert not list(pipe.service.runtime.library.glob('.pending_bgv_*'))
