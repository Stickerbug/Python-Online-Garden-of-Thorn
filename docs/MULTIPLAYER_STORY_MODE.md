# Cooperative Story Mode Contract

Status: schema foundation (`v10`), deterministic combat coordination,
independent party/run/action persistence, viewer-specific HTTP snapshots and a
staff/admin-only three-stage experiment are implemented locally. The
current two-seat flow uses HTTP polling, begins with a leader-owned difficulty
selection and two private personal blessings, then traverses deterministic
Garden, Jungle and Factory maps through curated combat/elite encounters,
personal rewards, rest, chests and shops, shared event/route decisions and
cooperative-specific bosses. Each stage ends at an explicit two-seat barrier;
only the third barrier produces the final `complete` result.

This is a complete three-stage Normal/Hard/Lunatic experimental contract,
not parity with every single-player card, relic, event, shop service, enemy or
boss script. Easy is fail-closed until its five per-seat talents are implemented.
Ordered Socket.IO reconnect, three/four-player play, Boss Rush, matchmaking and
spectators remain pending.

The cooperative mode extends the existing server-authoritative story state
machine. It does not reuse the PvP `GameEngine`/`GameEngine2v2` combat core and
does not change the live single-player schema (`v9`) until all story phases can
consume v10 safely.

## Shared content compilation

- `story_content.py` is the canonical catalog for both solo and cooperative
  story data. `story_coop_content.py` compiles only definitions that the current
  cooperative reducer can execute without changing their meaning.
- Compatible card costs, names, descriptions, images, upgrades and basic
  `damage`/`shield`/`active_discard` effects flow into cooperative play without
  a second value table. Reward and shop membership are derived from the solo
  pools; opening blessings are derived from their supported scripts.
- Compatible ordinary enemy names, images, health, Lunatic values and cyclic
  `damage`/`gain_shield`/`gain_power`/`self_damage` moves are compiled from the
  same catalog. Garden encounter groups enter the cooperative pool only when
  every member and every move can be represented exactly. The two-seat health
  multiplier is an explicit cooperative rule applied after compilation.
- Compatible relics are compiled from the same `STORY_RELICS` catalog. The
  current exact reducers cover the required Energetic floor heal plus Rich,
  Diligent, Greedy, Body Reinforcement and Bargaining. Personal chests and
  shops derive their relic pools, rarity, price, name, description and numeric
  effect from that manifest; `shop_excluded` is authoritative. Unknown relic
  fields or scripts fail closed instead of being approximated.
- Card scripts, unknown tags or fields and unsupported effect shapes fail
  closed. A definition may declare `coop.enabled` or `coop.required` to turn an
  incompatibility into a build-time error.
- Scripted enemies, traits, summons, ally selection, status application,
  death triggers and current Garden elite/Boss definitions remain outside the
  shared compiler. Elite and Boss nodes continue to use visibly distinct
  cooperative adapters until those mechanics have authoritative equivalents.
- The compiled manifest has a SHA-256 fingerprint embedded in the cooperative
  content version. Only the exact current fingerprint accepts live HTTP
  actions. Historical fingerprinted runs remain structurally readable for
  inspection or abandonment and are never reinterpreted as current content.
- Viewer UI resolves option and card text through the canonical story payload;
  it does not keep a second cooperative copy of names or numeric descriptions.
  A viewer receives only their own persistent relic list, chest relic and shop
  inventory. Teammates receive completion state without those identifiers.

## Access boundary

- The cooperative entry is rendered only for account roles `staff` and
  `admin`.
- Every cooperative HTTP and Socket.IO handler must repeat the server-side
  staff/admin check. Hiding a button is not authorization.
- Authorization failures use `404 / COOP_STORY_DISABLED` so unfinished routes
  are not advertised to ordinary accounts.
- The existing single-player story entry and APIs remain available to normal
  logged-in players.
- `GTN_STORY_COOP_ENABLED=0` disables both the entry and all cooperative APIs.

## MVP rules

- MVP party size: two. Schema and seat identifiers support up to four.
- Each seat owns its H/E/M, gold, talents, deck, hand, draw/discard/exile
  piles, equipment, statuses and rewards.
- Map, room, enemies, combat outcome, story flags and deterministic RNG are
  shared.
- Both living players act during one shared hero phase. Commands are accepted
  by one server queue and resolved in its authoritative sequence.
- A player may mark their seat ready. Enemies act only after every living seat
  is ready.
- Enemy intents include a stable target seat. A dead target is replaced by the
  next living seat in deterministic seat order.
- The party loses only when all seats are down. A downed player returns after a
  won combat with 20 percent of maximum H.
- Conflicting route votes resolve through the run's named RNG stream, never
  process-global randomness.
- Rewards, rest choices, chest contents and shop inventories are personal.
  Route votes and the current event decision are shared; submitted choices stay
  hidden until every required seat submits. A split shared-event vote applies
  no effect, consumes no RNG and reopens the choice until the party agrees.
- Cooperative card rewards and shop offers are compiled from the canonical
  single-player card pools.  The current executor accepts the exact shared
  damage, shield, active-discard, draw, elixir and exile semantics; changing a
  compatible card definition changes the compiled fingerprint and future runs,
  while unknown effects, scripts or tags remain unavailable by default.
- Shared events use the same canonical `STORY_EVENTS` definitions as solo
  story mode.  Only events whose policy and effect list can be represented by
  the cooperative reducer enter the biome pool; the viewer receives localized
  option copy but not server effect data or another seat's unresolved vote.
- No mid-combat join, AI takeover, public matchmaking, spectator mode, PvP
  mods or player replacement in the MVP.

## Persistent state

Illustrative v10 shape:

```json
{
  "schema_version": 10,
  "content_version": "<solo-content-version>-coop-stage1-shared-content-1-<fingerprint>",
  "mode": "coop",
  "phase": "combat",
  "party": {
    "leader_seat": 0,
    "max_players": 2,
    "members": [
      {
        "seat": 0,
        "user_id": 101,
        "username": "thorn-one",
        "display_name": "Thorn One",
        "membership_status": "active",
        "party_role": "leader"
      },
      {
        "seat": 1,
        "user_id": 202,
        "username": "bloom-two",
        "display_name": "Bloom Two",
        "membership_status": "active",
        "party_role": "member"
      }
    ],
    "rules": {
      "turn_model": "shared_hero_phase",
      "action_ordering": "server_serialized",
      "route_vote_policy": "seeded_random",
      "event_vote_policy": "unanimous_required"
    }
  },
  "players": {
    "0": {
      "health": 80,
      "max_health": 80,
      "elixir": 3,
      "magic": 0,
      "gold": 99,
      "deck": []
    },
    "1": {
      "health": 80,
      "max_health": 80,
      "elixir": 3,
      "magic": 0,
      "gold": 99,
      "deck": []
    }
  },
  "map": {},
  "room": {},
  "combat": null,
  "coordination": {
    "action_sequence": 0,
    "action_receipts": {},
    "combat_ready_seats": [],
    "combat_ready_round": null,
    "map_vote": null,
    "room_decision": null
  },
  "shared_reward": null,
  "rewards_by_player": null,
  "coop_progression": {
    "contract_version": 2,
    "chapter": 1,
    "encounter_index": 1,
    "max_floor": 16,
    "completed_combat_ids": [],
    "completed_node_ids": []
  },
  "room_states_by_player": null,
  "completed_stage": null,
  "rng_streams": {}
}
```

During combat, the shared field has this minimum shape:

```json
{
  "combat": {
    "id": "combat-0001",
    "round": 3,
    "turn": "heroes",
    "outcome": null,
    "enemies": [
      {
        "id": "enemy-1",
        "health": 24,
        "max_health": 40,
        "intent": {
          "kind": "attack",
          "amount": 7,
          "hits": 1,
          "target_seat": 1
        }
      }
    ],
    "seat_states": {
      "0": {
        "elixir": 2,
        "magic": 0,
        "shield": 4,
        "statuses": {},
        "hand": [],
        "draw_pile": [],
        "discard_pile": [],
        "exile_pile": [],
        "equipment": []
      },
      "1": {
        "elixir": 3,
        "magic": 0,
        "shield": 0,
        "statuses": {},
        "hand": [],
        "draw_pile": [],
        "discard_pile": [],
        "exile_pile": [],
        "equipment": []
      }
    }
  }
}
```

`players[seat]` owns journey-persistent health, deck, gold, talents and
relics. `combat.seat_states[seat]` owns only that seat's current-combat zones,
resources, shield and statuses. Enemies, round and outcome exist once and are
shared. The playable intro rekeys copied starter cards to run-stable, globally
unique combat instance IDs. Every card event still carries `actor_seat`,
because ownership is always authoritative and seat-scoped.

Account secrets, cookies, role metadata and client-provided seat numbers must
never enter the run state. A seat is assigned by the server and resolved from
the authenticated `user_id` for every command.

## Command and event envelopes

Combat command:

```json
{
  "party_id": "party-id",
  "run_id": "run-id",
  "action_id": "client-unique-id",
  "run_revision": 17,
  "combat_id": "combat-0001",
  "combat_round": 3,
  "expected_sequence": 41,
  "action_type": "play_card",
  "payload": {
    "card_instance_id": "sc-0001",
    "target_enemy_id": "enemy-1"
  }
}
```

Journey commands use the same envelope but must omit `combat_id` and
`combat_round`:

```json
{
  "party_id": "party-id",
  "run_id": "run-id",
  "action_id": "client-unique-id",
  "run_revision": 18,
  "expected_sequence": 42,
  "action_type": "reward_choose",
  "payload": {
    "reward_id": "reward:combat-0001:seat:0",
    "card_id": "bone"
  }
}
```

Supported journey payloads are deliberately identifier-only:

- `reward_choose`: `{reward_id, card_id}`. `card_id` may be empty to skip.
- `map_vote`: `{vote_id, node_id}` using one currently advertised route.
- Rest `room_choose`: `{room_id, choice}` for `heal`/`leave`, or
  `{room_id, choice:"upgrade", card_instance_id}` for one card in the actor's
  persistent deck.
- Chest `room_choose`: `{room_id, choice:"claim_gold"|"leave"}`.
- Event `room_choose`: `{room_id, choice:"mend"|"supplies"|"risk"}`.
- Shop `shop_buy`: `{room_id, offer_id}`; shop `room_choose` may only submit
  `{room_id, choice:"leave"}`.

The server derives the seat, validates the current phase and decision ID, and
recomputes health changes, rewards, prices and purchases. Clients never submit
`actor_*`, price, gold, damage, healing, event effects, next state or RNG data.

The client never submits `actor_user_id` or an authoritative seat. The server
derives both from the authenticated connection, then records them with the
accepted action.

Server acknowledgement/event:

```json
{
  "success": true,
  "duplicate": false,
  "events": [],
  "receipt": {
    "action_id": "client-unique-id",
    "action_sequence": 42,
    "resulting_revision": 18
  },
  "run": {
    "id": "run-id",
    "revision": 18,
    "snapshot": {}
  }
}
```

Duplicate `action_id` values from the same authenticated account return the
original receipt, including after a terminal action releases party membership;
reusing an ID with different content is a conflict. The canonical request
fingerprint includes the server-resolved seat, action type and payload, plus
combat ID/round only for combat actions. The database stores the engine receipt
without rewriting it.
The pure headless core retains a local receipt ledger for isolated tests. Live
HTTP actions clear that map before persistence and rely on the bounded database
action ledger instead of letting the in-state map grow without limit.

`revision` is the optimistic persistence revision carried by the run envelope;
it is not duplicated inside `state_json`. `coordination.action_sequence` is the
accepted domain-command order inside the v10 state. Every accepted command
increments both exactly once at their respective layers. A client that misses
one or more revisions requests a full viewer-specific snapshot. Invalid or
stale targets, rounds and sequences are rejected without changing state or RNG
counters.

Planned Socket.IO events:

- Client: `story_party_create`, `story_party_join`, `story_party_leave`,
  `story_party_ready`, `story_party_start`, `story_map_vote`,
  `story_room_choose`, `story_reward_choose`, `story_combat_action`,
  `story_combat_ready`, `story_rejoin_accept`.
- Server: `story_party_state`, `story_run_snapshot`, `story_run_events`,
  `story_action_ack`, `story_action_rejected`, `story_vote_state`,
  `story_member_disconnected`, `story_member_reconnected`.

Implemented staff/admin HTTP endpoints:

- `GET /api/story/coop/party`: return the authenticated member's current party
  and viewer-specific run snapshot, or `null` values.
- `POST /api/story/coop/party`: create a two-seat forming party. The leader is
  always server-assigned seat zero.
- `POST /api/story/coop/party/join`: join by a high-entropy invite token; both
  account and IP attempts are rate-limited.
- `POST /api/story/coop/party/invite`: leader-only invite rotation for a
  forming party.
- `POST /api/story/coop/party/leave`: dissolve a forming party and release all
  memberships.
- `POST /api/story/coop/party/start`: leader-only creation of one v10 run in
  `journey_setup` after both memberships and roles are rechecked in the
  transaction. Difficulty selection remains a separately idempotent run action.
- `POST /api/story/coop/party/abandon`: atomically abandon an active
  experimental run, close its party and release both memberships.
- `GET /api/story/coop/run/<run_id>`: return a strict viewer projection for a
  current or historical member. It never returns the server seed, RNG streams,
  draw order or the internal receipt ledger.
- `POST /api/story/coop/run/<run_id>/action`: derive the actor from the logged-in
  account, dispatch setup, private opening, combat, reward, route, room or shop
  intent, commit it with
  run-revision CAS and return the new viewer-specific snapshot. Ambiguous
  retries reuse the same `action_id`. Combat fields are required only for
  `play_card`/`combat_ready` and forbidden for all journey actions.

Invite plaintext is returned only by create/rotate and is never stored. If a
response is lost, the leader rotates the token; the previous token becomes
invalid. Every party response uses `Cache-Control: private, no-store`.

## Invariants

1. Seats are contiguous integers starting at zero and are stable for a run.
2. `party.members[*].seat` and `players` keys match exactly.
3. A user occupies at most one seat.
4. Only a member may read or mutate a party run.
5. Only the server assigns actor and seat information.
6. Every accepted command increments one global run revision and one
   `action_sequence` exactly once; all events from that command carry the same
   `action_sequence` and a consecutive `event_index`.
7. All random decisions use the run seed and named RNG stream counters.
8. Player-private zones are projected per viewer even when the room setting
   currently exposes teammate hands.
9. A combat transition to the enemy phase occurs once, after all living seats
   are ready.
10. Automatic persistence is authoritative; manual load remains map-only and
    requires unanimous active-member approval.
11. A combat command carries the current `combat_id` and `combat_round`; a
    delayed command from an earlier combat or round is rejected atomically.
12. `combat_ready_seats` is a sorted unique subset of living seats and is bound
    to `combat_ready_round`; party-lobby readiness is a separate field.
13. Enemy single-target intents persist `target_seat`. If that seat is down,
    resolution walks forward through seat order and wraps without consuming
    RNG. Remaining hits in the same multi-hit intent follow that deterministic
    retarget rather than disappearing. Newly selected targets use a named
    deterministic RNG stream.
14. Health is clamped to `[0, max_health]`. Zero health is the sole downed
    truth; all-down defeat takes priority over simultaneous last-enemy defeat.
    After victory, downed seats revive to `max(1, ceil(max_health * 0.20))`
    before reward snapshots are created.
15. A won non-final combat changes to `reward` in the same accepted action.
    Each viewer receives only their own card options; teammates expose only a
    resolved/pending bit.
16. The last personal reward choice atomically creates a route vote from the
    current map node's actual outgoing edges. Submitted targets remain private
    until the last vote resolves.
17. Unanimous route votes consume no RNG. Split votes consume exactly one
    named `coop_route_vote:*` stream step and choose only among nodes that were
    actually voted for. The last vote enters the selected combat or room in
    the same revision.
18. Rest, chest and shop state is per seat. A viewer receives only their own
    deck/options, chest amount or shop offers; teammate state is reduced to a
    completion bit. The last seat to finish atomically opens the next route
    vote.
19. Event votes expose only submitted bits before resolution. Only a unanimous
    shared-event choice may apply effects. A split applies nothing, consumes no
    RNG, clears that decision round and reopens the same choices for every seat.
20. Each biome boss uses a distinct cooperative definition and deliberately
    scoped rules. Winning marks the terminal node complete and persists
    `stage_complete` while the run and party remain active. Each member submits
    one `stage_ready`; only the second confirmation advances atomically.
21. Public snapshots and event batches never include the run seed, RNG stream
    counters, draw-pile order, internal action receipts/fingerprints, another
    seat's reward selection, private room inventory or unresolved vote target.
22. Persisted content versions are routed through explicit validators. Frozen
    and historical fingerprinted contracts remain readable, but only the exact
    current full-journey content fingerprint accepts new HTTP actions.
23. A newly started run remains in `journey_setup`. Only the authenticated
    leader seat may submit `setup_start`, and only one of the server-advertised
    Normal, Hard or Lunatic identifiers is accepted. Easy is rejected rather
    than silently falling back to Normal.
24. The selected difficulty creates a private two-seat opening barrier on the
    real floor-one blessing node. Each viewer receives only their own three
    blessing identifiers plus per-seat completion bits. The chosen identifier
    is absent from shared events.
25. The last opening choice atomically completes floor one and creates a route
    vote for floor two. It does not create a fictitious floor-one combat or
    increment the completed-combat list.
26. For this cooperative contract Hard uses the hard map weights, 75 percent
    combat gold and 110 percent shop prices. Lunatic inherits those rules and
    scales curated enemy maximum H and attack intent by 125 percent. These are
    explicit cooperative rules, not a claim of full single-player difficulty
    parity.
27. Stage one and two confirmations heal each member by the same transition
    rule as solo story (full on Normal; at least 80 percent on Hard/Lunatic),
    generate the next biome map from the same run seed and start a new private
    blessing barrier. Decks, relics, gold and health otherwise persist.
28. Only stage-three dual confirmation sets `completed=true`. The final action,
    action receipt, run close, party/member release and one idempotent
    `story_progress_completions` row per member are committed in one SQLite
    transaction. Stage barriers, defeat and identical retries cannot award a
    clear twice.
29. Jungle and Factory canonical encounters are still `deferred` when their
    solo scripts/traits cannot be expressed exactly. Their playable fallback
    encounters use distinct `coop_*` ids and explicit cooperative values, so a
   simplified adapter is never presented as the original solo enemy. Compiler
   coverage still expands automatically when canonical mechanics become exact.
30. Enchantment books are cooperative-story progression only. Each member owns
    at most three private book instances, may discard them in or out of combat,
    and receives private combat/shop offers. Card enchantments share the solo
    definitions, including Puncture replay, Fire turn-start damage, Snatch's
    two private card-reward rounds and automatic Magic Yggdrasil protection.
    Books and book discovery are never projected into PvP state or the PvP
    compendium.
31. Solo story is the source of truth for all non-cooperative-specific content,
    rules, presentation and UI behavior. Cooperative story reuses those shared
    definitions and components; only party coordination, ownership/privacy,
    voting, synchronization and other inherently multiplayer rules may diverge.

## v9 compatibility

- Live single-player runs stay v9 for now.
- A non-combat v9 state can be copied into a one-seat v10 party for migration
  testing. The source object is never mutated.
- In-combat migration is rejected until the mixed v9 combat object has been
  split into shared enemy data and per-seat private zones.
- A migration is published only after replaying representative v9 saves
  through every phase and proving that v9 users can continue or abandon their
  existing runs.

## Delivery order and gates

1. **Schema foundation**: pure v10 builder, validation, safe one-seat wrapper,
   staff/admin entry and authorization tests.
2. **Combat rules slice**: two seats, shared hero phase, serialized play,
   ready barrier, deterministic enemy targets, down/all-down/revive, starter
   Basic/Rose/Amulet rules and deterministic discard/shuffle/draw are
   implemented for a curated cooperative Garden card/enemy set.
3. **Party persistence**: party/member/run/action tables, actor-aware receipts,
   private rotating invite, stable seat restore and atomic close/release are
   implemented.
4. **HTTP stage transport**: strict viewer snapshots, CAS/idempotent action
   transport, historical terminal reads and the independent staff/admin combat
   dialog are implemented. Personal rewards, private completion status, shared
   route voting and atomic node transitions are implemented.
   Ordered Socket.IO commands and reconnect remain a later realtime enhancement.
5. **Three-stage loop**: leader difficulty selection, private personal
   blessings, deterministic map traversal, personal rest,
   chest and shop rooms, one shared hidden-vote consensus event, curated normal/elite
   combats, cooperative-specific bosses, stage barriers and final per-member
   progress commits are implemented across Garden, Jungle and Factory.
   Safe cards, reward/shop pools, opening blessings and compatible ordinary
   enemies/encounters compile from the single-player content catalog. Scripted
   elite/Boss encounters, relic/shop-service/event parity remain later content
   expansions.
6. **UI and balance**: party lobby, teammate rails, target indicators,
   combat/reward/route/room panels and responsive layouts are implemented;
   richer enemy rules, configurable scaling and browser playtest tuning remain
   pending.
7. **Expansion**: three/four players, Boss Rush, matchmaking and spectator mode
   only after the two-player gates pass.

Each phase must preserve deterministic replay, action idempotency, actor
authorization, old-revision behavior, disconnect recovery and unchanged v9
single-player tests.
