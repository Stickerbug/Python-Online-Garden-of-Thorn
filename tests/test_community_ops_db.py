import gc
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import db
from community_ops import (
    CommunityOpsError,
    cast_community_poll_vote,
    create_community_announcement,
    create_community_chain,
    create_community_poll,
    get_community_feed,
    join_community_chain,
    list_community_ops_workspace,
    mutate_community_announcement,
    mutate_community_chain,
    mutate_community_poll,
)


class CommunityOpsPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'community.sqlite3')
        db.init_db()
        self.staff, error = db.create_user('CommunityStaff', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.voter, error = db.create_user('CommunityVoter', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.actor = {
            'user_id': self.staff['id'],
            'username': self.staff['username'],
            'role_type': 'staff',
        }

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    @staticmethod
    def iso_after(hours):
        return (
            datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=hours)
        ).isoformat().replace('+00:00', 'Z')

    def test_published_announcement_and_changelog_draft_are_audited(self):
        item = create_community_announcement(
            self.actor,
            title='维护完成',
            body='服务器已经恢复开放。',
            pinned=True,
            publish=True,
            changelog_draft=True,
        )

        feed = get_community_feed()
        workspace = list_community_ops_workspace()

        self.assertEqual(feed['announcements'][0]['id'], item['id'])
        self.assertTrue(feed['announcements'][0]['pinned'])
        self.assertEqual(workspace['changelog_drafts'][0]['announcement_id'], item['id'])
        self.assertEqual(workspace['changelog_drafts'][0]['status'], 'pending')
        self.assertEqual(workspace['audit'][0]['action'], 'announcement_create')
        self.assertNotIn('created_by', feed['announcements'][0])

    def test_future_announcement_is_hidden_and_schedule_requires_explicit_start(self):
        item = create_community_announcement(
            self.actor,
            title='未来公告',
            body='尚未到展示时间。',
            starts_at=self.iso_after(2),
            publish=True,
        )
        self.assertEqual(get_community_feed()['announcements'], [])

        draft = create_community_announcement(
            self.actor,
            title='草稿',
            body='等待定时发布。',
        )
        with self.assertRaisesRegex(CommunityOpsError, '必须填写开始时间'):
            mutate_community_announcement(self.actor, draft['id'], 'schedule')
        self.assertGreater(item['id'], 0)

    def test_active_poll_hides_results_and_vote_is_immutable(self):
        poll = create_community_poll(
            self.actor,
            question='选择新的活动时间？',
            options=['周六', '周日'],
            ends_at=self.iso_after(2),
            reminder_hours=3,
            publish=True,
        )
        option_a, option_b = [option['id'] for option in poll['options']]

        public_poll = get_community_feed(self.voter['id'])['polls'][0]
        self.assertTrue(public_poll['can_vote'])
        self.assertNotIn('vote_count', public_poll['options'][0])

        voted, duplicate = cast_community_poll_vote(self.voter['id'], poll['id'], option_a)
        self.assertFalse(duplicate)
        self.assertEqual(voted['selected_option_id'], option_a)
        voted, duplicate = cast_community_poll_vote(self.voter['id'], poll['id'], option_a)
        self.assertTrue(duplicate)
        with self.assertRaisesRegex(CommunityOpsError, '不能改票'):
            cast_community_poll_vote(self.voter['id'], poll['id'], option_b)

        closed, duplicate = mutate_community_poll(self.actor, poll['id'], 'close')
        self.assertFalse(duplicate)
        self.assertEqual(closed['effective_state'], 'closed')
        self.assertEqual(sum(option['vote_count'] for option in closed['options']), 1)
        with self.assertRaisesRegex(CommunityOpsError, '已经结束'):
            cast_community_poll_vote(self.staff['id'], poll['id'], option_b)

    def test_poll_schedule_requires_explicit_start(self):
        poll = create_community_poll(
            self.actor,
            question='草稿投票？',
            options=['A', 'B'],
            ends_at=self.iso_after(4),
        )
        with self.assertRaisesRegex(CommunityOpsError, '必须填写开始时间'):
            mutate_community_poll(self.actor, poll['id'], 'schedule')

    def test_ended_poll_feed_visibility_can_be_controlled_from_backend(self):
        recent = create_community_poll(
            self.actor,
            question='刚结束的投票',
            options=['A', 'B'],
            starts_at=self.iso_after(-100),
            ends_at=self.iso_after(-10),
            publish=True,
        )
        old = create_community_poll(
            self.actor,
            question='结束很久的投票',
            options=['A', 'B'],
            starts_at=self.iso_after(-200),
            ends_at=self.iso_after(-100),
            publish=True,
        )
        self.assertIn(recent['id'], [item['id'] for item in get_community_feed()['polls']])
        self.assertNotIn(old['id'], [item['id'] for item in get_community_feed()['polls']])

        hidden, _ = mutate_community_poll(self.actor, recent['id'], 'feed_hide')
        self.assertEqual(hidden['feed_visibility'], 'hide')
        self.assertNotIn(recent['id'], [item['id'] for item in get_community_feed()['polls']])
        self.assertIn(recent['id'], [
            item['id']
            for item in list_community_ops_workspace()['polls']
        ])

        shown, _ = mutate_community_poll(self.actor, old['id'], 'feed_show')
        self.assertEqual(shown['feed_visibility'], 'show')
        self.assertIn(old['id'], [item['id'] for item in get_community_feed()['polls']])

        restored, _ = mutate_community_poll(self.actor, recent['id'], 'feed_auto')
        self.assertEqual(restored['feed_visibility'], 'auto')
        self.assertIn(recent['id'], [item['id'] for item in get_community_feed()['polls']])

    def test_chain_join_is_once_per_user_and_feed_marks_own_entry(self):
        second, error = db.create_user('ChainTwo', 'Aa1!aaaa')
        self.assertIsNone(error)
        chain = create_community_chain(
            self.actor,
            title='希望增加的玩法',
            description='每人接龙一条自己的建议。',
            publish=True,
        )
        self.assertEqual(chain['effective_state'], 'active')

        feed = get_community_feed(self.voter['id'])
        public_chain = feed['chains'][0]
        self.assertTrue(public_chain['can_join'])
        self.assertIsNone(public_chain['my_entry'])

        joined, duplicate = join_community_chain(
            self.voter['id'],
            chain['id'],
            '我想玩无尽模式',
        )
        self.assertFalse(duplicate)
        self.assertEqual(joined['entry_count'], 1)
        self.assertEqual(joined['my_entry'], '我想玩无尽模式')

        joined, duplicate = join_community_chain(
            self.voter['id'],
            chain['id'],
            '我改成了团队合作模式',
        )
        self.assertTrue(duplicate)
        self.assertEqual(joined['entry_count'], 1)
        self.assertEqual(joined['my_entry'], '我改成了团队合作模式')

        second_chain, _ = join_community_chain(
            second['id'],
            chain['id'],
            '我想要每日任务',
        )
        self.assertEqual(second_chain['entry_count'], 2)
        self.assertEqual(second_chain['entries'][1]['nickname'], second['username'])

        workspace = list_community_ops_workspace()
        self.assertEqual(workspace['chains'][0]['id'], chain['id'])
        self.assertEqual(workspace['audit'][0]['action'], 'chain_create')

        closed, duplicate = mutate_community_chain(self.actor, chain['id'], 'close')
        self.assertFalse(duplicate)
        self.assertEqual(closed['effective_state'], 'closed')
        with self.assertRaisesRegex(CommunityOpsError, '已经结束'):
            join_community_chain(self.staff['id'], chain['id'], '不能继续接龙')


if __name__ == '__main__':
    unittest.main()
