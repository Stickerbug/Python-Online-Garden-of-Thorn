# Cooperative Story Mode Contract

Status: schema foundation (`v10`), deterministic headless combat coordination,
independent party/run/action persistence and a staff/admin-only HTTP party
lobby are implemented locally. Realtime transport and the playable
cooperative journey are not connected yet.

The cooperative mode extends the existing server-authoritative story state
machine. It does not reuse the PvP `GameEngine`/`GameEngine2v2` combat core and
does not change the live single-player schema (`v9`) until all story phases can
consume v10 safely.

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
- Rewards and shops are personal. Shared chest priority rotates by seat.
- No mid-combat join, AI takeover, public matchmaking, spectator mode, PvP
  mods or player replacement in the MVP.

## Persistent state

Illustrative v10 shape:

```json
{
  "schema_version": 10,
  "content_version": "story-redesign-9",
  "mode": "coop",
  "phase": "journey_setup",
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
      "route_vote_policy": "seeded_random"
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
shared. Card instance identity is scoped as `(seat, instance_id)` until global
instance IDs are introduced; every card event therefore carries `actor_seat`.

Account secrets, cookies, role metadata and client-provided seat numbers must
never enter the run state. A seat is assigned by the server and resolved from
the authenticated `user_id` for every command.

## Command and event envelopes

Client command:

```json
{
  "party_id": "party-id",
  "run_id": "run-id",
  "action_id": "client-unique-id",
  "last_revision": 17,
  "combat_id": "combat-0001",
  "combat_round": 3,
  "action_type": "play_card",
  "payload": {
    "card_instance_id": "sc-0001",
    "target_kind": "enemy",
    "target_id": "enemy-1"
  }
}
```

The client never submits `actor_user_id` or an authoritative seat. The server
derives both from the authenticated connection, then records them with the
accepted action.

Server acknowledgement/event:

```json
{
  "party_id": "party-id",
  "run_id": "run-id",
  "action_id": "client-unique-id",
  "revision": 18,
  "action_sequence": 42,
  "events": [],
  "snapshot": null
}
```

Duplicate `action_id` values from the same authenticated account return the
original receipt, including after a terminal action releases party membership;
reusing an ID with different content is a conflict. The canonical request
fingerprint includes the server-resolved seat, combat ID, combat round, action
type and payload. The database stores the engine receipt without rewriting it.
The headless state still retains a local receipt ledger for pure-engine tests;
live transport must rely on the bounded database action ledger instead of
letting the in-state map grow without limit.

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

Implemented staff/admin HTTP party endpoints:

- `GET /api/story/coop/party`: return the authenticated member's current party
  and run, or `null` values.
- `POST /api/story/coop/party`: create a two-seat forming party. The leader is
  always server-assigned seat zero.
- `POST /api/story/coop/party/join`: join by a high-entropy invite token; both
  account and IP attempts are rate-limited.
- `POST /api/story/coop/party/invite`: leader-only invite rotation for a
  forming party.
- `POST /api/story/coop/party/leave`: dissolve a forming party and release all
  memberships.
- `POST /api/story/coop/party/start`: leader-only creation of one v10 run after
  both members and both staff/admin roles are rechecked in the transaction.
- `POST /api/story/coop/party/abandon`: atomically abandon an active
  experimental run, close its party and release both memberships.

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
2. **Headless combat slice**: two seats, shared hero phase, serialized play,
   ready barrier, deterministic enemy targets, down/all-down/revive. The
   coordination core is implemented; full story-card/enemy adapters remain a
   gate before this phase is complete.
3. **Party persistence**: party/member/run/action tables, actor-aware receipts,
   private rotating invite, stable seat restore and atomic close/release are
   implemented. The staff/admin HTTP lobby is the current local control plane.
4. **Realtime transport**: ordered Socket.IO commands, revision recovery,
   reconnect and full snapshot fallback.
5. **Complete first-stage slice**: map voting, events, rest, shop, chest,
   personal rewards and boss.
6. **UI and balance**: the experimental party-lobby dialog is implemented;
   teammate rail, target indicators, mobile combat layouts, cooperative cards
   and configurable scaling remain pending.
7. **Expansion**: three/four players, full journey, Boss Rush, matchmaking and
   spectator mode only after the two-player gates pass.

Each phase must preserve deterministic replay, action idempotency, actor
authorization, old-revision behavior, disconnect recovery and unchanged v9
single-player tests.
