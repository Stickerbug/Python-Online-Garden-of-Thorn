(() => {
  'use strict';

  const T = {
    zh: {
      fb_tab: '管理员/申诉', fb_send: '联系管理员', fb_staff: '查看管理员反馈', fb_handling: '举报处理',
      fb_category_account: '账号问题', fb_category_report: '举报/纠纷', fb_category_appeal: '对局申诉',
      fb_title_placeholder: '标题', fb_replay_placeholder: '回放 ID，例如 R-12345 或 P-12345',
      fb_message_placeholder: '输入反馈内容...', fb_send_btn: '发送',
      fb_status_open: '未处理', fb_status_pending: '已回复', fb_status_closed: '已关闭',
      fb_login_required: '登录账号后可以发送反馈。', fb_empty: '暂无反馈。', fb_staff_empty: '暂无玩家反馈。',
      fb_sent: '反馈已发送', fb_select_thread: '选择一条玩家反馈。', fb_compose_hint: '填写内容后发送新的反馈。',
      fb_replay_view: '查看', fb_replay_load_failed: '回放加载失败', fb_replay_unavailable: '回放不存在或已过期',
      fb_admin_prefix: '管理员', fb_request_failed: '请求失败',
      feedback_center: '反馈中心', bug_tab: '漏洞', suggestion_tab: '建议', internal_tab: '不公开', internal_kind: '不公开反馈', project_subtitle: '漏洞与建议',
      project_copy: '报告漏洞，或为未来的更新提出建议。登录后可投票与讨论。',
      status: '状态', all_status: '全部状态', sort: '排序',
      results: '共 {0} 条',
      sort_priority: '优先级', sort_recent: '最新', sort_votes: '票数', sort_updated: '最近更新',
      prev: '上一页', next: '下一页', empty: '还没有公开反馈。', loading: '加载中…',
      select_detail: '选择一个问题查看详情', new_report: '新建反馈', back_list: '返回列表',
      back_game: '返回游戏主页', votes: '票', vote: '投票', remove_vote: '取消投票',
      comments: '评论', login_hint: '登录账号后可以发布、评论或投票。', guest_more: '登录后查看全部 {0} 条评论。',
      comment_placeholder: '写下你的评论…', send: '发送', edit: '编辑', delete: '删除',
      save: '保存', cancel: '取消', private_title: '私密补充（仅作者与 Staff 可见）',
      private_placeholder: '补充不公开的信息…', staff_zone: 'Staff 管理', reason: '公开原因',
      priority: '优先级', pin: '置顶', unpin: '取消置顶', hide_issue: '隐藏反馈',
      unhide_issue: '恢复反馈', hide_comment: '隐藏评论', unhide_comment: '恢复评论',
      internal_note: '内部备注', history: '状态历史', deleted_player: '已注销玩家',
      author: '发布者', updated: '更新于 {0}', login: '去登录', account_label: '账号',
      watch: '关注', watched: '已关注', rail_details: '详情', rail_version: '游戏版本',
      rail_fix_version: '修复版本', rail_tags: '标签', rail_related: '关联问题',
      rail_watchers: '关注人数', rail_replay: '回放',
      ago_now: '刚刚', ago_min: '{0} 分钟前', ago_hour: '{0} 小时前', ago_day: '{0} 天前',
      ago_week: '{0} 周前', ago_month: '{0} 个月前',
      messages_title: '消息', messages_empty: '暂无新消息',
      messages_login: '请先登录账号后查看消息。', messages_back: '返回反馈列表',
      messages_mark_all_read: '全部已读',
      mark_read: '标为已读', notification_status: '状态', notification_comment: '新评论',
      notification_private: '私密补充', notification_reopen: '仍未修复请求',
      notification_staff: '待处理请求', notification_watched: '关注更新', notification_author: '你的反馈更新',
      report: '举报', report_comment: '举报评论', report_title: '举报', submit_report: '提交举报',
      replay_hint: '回放 ID：{0}（登录游戏后可查看）', need_login: '请先登录账号。',
      own_issue: '不能给自己的问题投票',
      guest_notice: '游客可浏览全文；评论与投票需要登录。',
      report_cat_abusive_language: '不当言语', report_cat_sexual_content: '色情内容',
      report_cat_spam: '刷屏/广告', report_cat_privacy_leak: '泄露隐私',
      report_cat_harassment: '骚扰', report_cat_misleading: '误导/虚假',
      report_cat_duplicate: '重复/已存在', report_cat_other: '其他',
      bug_status: { new: '待确认', needs_info: '需补充', confirmed: '已确认', in_progress: '修复中', fixed: '已修复', duplicate: '重复', unreproducible: '无法复现', by_design: '设计如此', invalid: '不予处理' },
      suggestion_status: { new: '待审核', under_review: '审核中', accepted: '已采纳', partially_accepted: '采纳一半', planned: '已规划', rejected: '已拒绝', duplicate: '重复' },
      internal_status: { new: '待处理', needs_info: '需补充', in_progress: '处理中', fixed: '已完成', duplicate: '重复', invalid: '无效' },
    },
    en: {
      fb_tab: 'Admin / Report', fb_send: 'Contact Admin', fb_staff: 'View Admin Messages', fb_handling: 'Moderation',
      fb_category_account: 'Account support', fb_category_report: 'Report / Dispute', fb_category_appeal: 'Match appeal',
      fb_title_placeholder: 'Title', fb_replay_placeholder: 'Replay ID, e.g. R-12345 or P-12345',
      fb_message_placeholder: 'Type your message...', fb_send_btn: 'Send',
      fb_status_open: 'Open', fb_status_pending: 'Replied', fb_status_closed: 'Closed',
      fb_login_required: 'Sign in to send feedback.', fb_empty: 'No feedback yet.', fb_staff_empty: 'No player feedback.',
      fb_sent: 'Feedback sent', fb_select_thread: 'Select a player feedback thread.', fb_compose_hint: 'Fill in and send new feedback.',
      fb_replay_view: 'View', fb_replay_load_failed: 'Failed to load replay', fb_replay_unavailable: 'Replay unavailable or expired',
      fb_admin_prefix: 'Admin', fb_request_failed: 'Request failed',
      feedback_center: 'Feedback Center', bug_tab: 'Bugs', suggestion_tab: 'Suggestions', internal_tab: 'Internal', internal_kind: 'Internal feedback', project_subtitle: 'Bugs & suggestions',
      project_copy: 'Report bugs or propose updates. Sign in to vote and discuss.',
      status: 'Status', all_status: 'All statuses', sort: 'Sort',
      results: '{0} results',
      sort_priority: 'Priority', sort_recent: 'Newest', sort_votes: 'Votes', sort_updated: 'Recently updated',
      prev: 'Previous', next: 'Next', empty: 'No reports yet.', loading: 'Loading…',
      select_detail: 'Select a report to view details.', new_report: 'New report', back_list: 'Back to list',
      back_game: 'Back to game', votes: 'votes', vote: 'Vote', remove_vote: 'Remove vote',
      comments: 'Comments', login_hint: 'Sign in to post, comment or vote.',
      guest_more: 'Sign in to view all {0} comments.',
      comment_placeholder: 'Write a comment…', send: 'Send', edit: 'Edit', delete: 'Delete',
      save: 'Save', cancel: 'Cancel', private_title: 'Private supplement (author & staff)',
      private_placeholder: 'Private information…', staff_zone: 'Staff controls', reason: 'Public reason',
      priority: 'Priority', pin: 'Pin', unpin: 'Unpin', hide_issue: 'Hide report',
      unhide_issue: 'Restore report', hide_comment: 'Hide comment', unhide_comment: 'Restore comment',
      internal_note: 'Internal note', history: 'Status history', deleted_player: 'Deleted Player',
      author: 'Reported by', updated: 'Updated {0}', login: 'Sign in', account_label: 'Account',
      watch: 'Watch', watched: 'Watching', rail_details: 'Details', rail_version: 'Game version',
      rail_fix_version: 'Fixed in', rail_tags: 'Labels', rail_related: 'Related',
      rail_watchers: 'Watchers', rail_replay: 'Replay',
      ago_now: 'just now', ago_min: '{0}m ago', ago_hour: '{0}h ago', ago_day: '{0}d ago',
      ago_week: '{0}w ago', ago_month: '{0}mo ago',
      messages_title: 'Messages', messages_empty: 'No new messages',
      messages_login: 'Sign in to view your messages.', messages_back: 'Back to reports',
      messages_mark_all_read: 'Mark all read',
      mark_read: 'Mark read', notification_status: 'Status', notification_comment: 'New comment',
      notification_private: 'Private note', notification_reopen: 'Not-fixed request',
      notification_staff: 'Pending request', notification_watched: 'Watched update', notification_author: 'Your report update',
      report: 'Report', report_comment: 'Report comment', report_title: 'Report', submit_report: 'Submit report',
      replay_hint: 'Replay ID: {0} (viewable in game)', need_login: 'Sign in to continue.',
      own_issue: 'You cannot vote on your own report',
      guest_notice: 'Guests can browse. Comments and votes require sign-in.',
      report_cat_abusive_language: 'Abusive language', report_cat_sexual_content: 'Sexual content',
      report_cat_spam: 'Spam', report_cat_privacy_leak: 'Privacy leak',
      report_cat_harassment: 'Harassment', report_cat_misleading: 'Misleading',
      report_cat_duplicate: 'Duplicate / already reported', report_cat_other: 'Other',
      bug_status: { new: 'New', needs_info: 'Needs info', confirmed: 'Confirmed', in_progress: 'Fixing', fixed: 'Fixed', duplicate: 'Duplicate', unreproducible: 'Cannot reproduce', by_design: 'Works as intended', invalid: 'Invalid' },
      suggestion_status: { new: 'New', under_review: 'Under review', accepted: 'Accepted', partially_accepted: 'Partially adopted', planned: 'Planned', rejected: 'Declined', duplicate: 'Duplicate' },
      internal_status: { new: 'New', needs_info: 'Needs info', in_progress: 'In progress', fixed: 'Done', duplicate: 'Duplicate', invalid: 'Invalid' },
    },
    fr: {
      fb_tab: 'Admin / Signalement', fb_send: "Contacter l'admin", fb_staff: 'Voir les messages admin', fb_handling: 'Modération',
      fb_category_account: 'Problème de compte', fb_category_report: 'Signalement / litige', fb_category_appeal: 'Appel de partie',
      fb_title_placeholder: 'Titre', fb_replay_placeholder: 'ID du replay, ex. R-12345 ou P-12345',
      fb_message_placeholder: 'Écrivez votre message...', fb_send_btn: 'Envoyer',
      fb_status_open: 'Ouvert', fb_status_pending: 'Répondu', fb_status_closed: 'Fermé',
      fb_login_required: 'Connectez-vous pour envoyer un feedback.', fb_empty: 'Aucun feedback.', fb_staff_empty: 'Aucun feedback joueur.',
      fb_sent: 'Feedback envoyé', fb_select_thread: 'Sélectionnez un feedback joueur.', fb_compose_hint: 'Remplissez et envoyez un nouveau feedback.',
      fb_replay_view: 'Voir', fb_replay_load_failed: 'Échec du replay', fb_replay_unavailable: 'Replay indisponible ou expiré',
      fb_admin_prefix: 'Admin', fb_request_failed: 'Échec de la requête',
      feedback_center: 'Centre de signalements', bug_tab: 'Bugs', suggestion_tab: 'Suggestions', internal_tab: 'Interne', internal_kind: 'Signalement interne', project_subtitle: 'Bugs et suggestions',
      project_copy: 'Signalez un bug ou proposez une amélioration. Connectez-vous pour voter.',
      status: 'Statut', all_status: 'Tous', sort: 'Trier', sort_priority: 'Priorité',
      results: '{0} résultats',
      sort_recent: 'Récents', sort_votes: 'Votes', sort_updated: 'Mises à jour',
      prev: 'Précédent', next: 'Suivant', empty: 'Aucun signalement.', loading: 'Chargement…',
      select_detail: 'Choisissez un signalement.', new_report: 'Nouveau signalement',
      back_list: 'Retour', back_game: 'Retour au jeu', votes: 'votes', vote: 'Voter',
      remove_vote: 'Retirer le vote', comments: 'Commentaires',
      login_hint: 'Connectez-vous pour publier ou voter.',
      guest_more: 'Connectez-vous pour voir les {0} commentaires.',
      comment_placeholder: 'Commentaire…', send: 'Envoyer', edit: 'Modifier', delete: 'Supprimer',
      save: 'Enregistrer', cancel: 'Annuler', private_title: 'Complément privé (auteur et Staff)',
      private_placeholder: 'Informations privées…', staff_zone: 'Contrôles Staff', reason: 'Raison publique',
      priority: 'Priorité', pin: 'Épingler', unpin: 'Désépingler', hide_issue: 'Masquer',
      unhide_issue: 'Restaurer', hide_comment: 'Masquer le commentaire', unhide_comment: 'Restaurer',
      internal_note: 'Note interne', history: 'Historique', deleted_player: 'Joueur supprimé',
      author: 'Auteur', updated: 'Mis à jour {0}', login: 'Connexion', account_label: 'Compte',
      messages_mark_all_read: 'Tout marquer lu',
      mark_read: 'Marquer lu', notification_status: 'Statut', notification_comment: 'Nouveau commentaire',
      notification_private: 'Note privée', notification_reopen: 'Signalement « non réparé »',
      watch: 'Suivre', watched: 'Suivi', rail_details: 'Détails', rail_version: 'Version du jeu',
      rail_fix_version: 'Corrigé dans', rail_tags: 'Étiquettes', rail_related: 'Liens',
      rail_watchers: 'Suiveurs', rail_replay: 'Replay',
      ago_now: 'à l’instant', ago_min: 'il y a {0} min', ago_hour: 'il y a {0} h', ago_day: 'il y a {0} j',
      ago_week: 'il y a {0} sem.', ago_month: 'il y a {0} mois',
      report: 'Signaler', report_comment: 'Signaler le commentaire', report_title: 'Signaler',
      submit_report: 'Envoyer', replay_hint: 'ID de partie : {0}', need_login: 'Connectez-vous.',
      own_issue: 'Vous ne pouvez pas voter sur votre propre signalement.',
      guest_notice: 'Visiteurs : lecture seule.',
      report_cat_abusive_language: 'Langage abusif', report_cat_sexual_content: 'Contenu sexuel',
      report_cat_spam: 'Spam', report_cat_privacy_leak: 'Vie privée', report_cat_harassment: 'Harcèlement',
      report_cat_misleading: 'Trompeur', report_cat_duplicate: 'Doublon', report_cat_other: 'Autre',
      bug_status: { new: 'Nouveau', needs_info: 'Infos requises', confirmed: 'Confirmé', in_progress: 'Correction', fixed: 'Corrigé', duplicate: 'Doublon', unreproducible: 'Non reproduit', by_design: 'Prévu', invalid: 'Invalide' },
      suggestion_status: { new: 'Nouveau', under_review: 'À l’étude', accepted: 'Accepté', partially_accepted: 'Partiellement adopté', planned: 'Planifié', rejected: 'Refusé', duplicate: 'Doublon' },
      internal_status: { new: 'Nouveau', needs_info: 'Infos requises', in_progress: 'En cours', fixed: 'Terminé', duplicate: 'Doublon', invalid: 'Invalide' },
    },
    ja: {
      fb_tab: '管理者・通報', fb_send: '管理者に問い合わせ', fb_staff: '管理者メッセージ確認', fb_handling: '通報管理',
      fb_category_account: 'アカウント問題', fb_category_report: '通報・紛争', fb_category_appeal: '対戦申立',
      fb_title_placeholder: 'タイトル', fb_replay_placeholder: 'リプレイID（例 R-12345 / P-12345）',
      fb_message_placeholder: 'メッセージを入力...', fb_send_btn: '送信',
      fb_status_open: '未対応', fb_status_pending: '返信済み', fb_status_closed: '終了',
      fb_login_required: 'ログインすると送信できます。', fb_empty: 'まだありません。', fb_staff_empty: 'プレイヤー feedback はありません。',
      fb_sent: '送信しました', fb_select_thread: 'プレイヤーの報告を選択してください。', fb_compose_hint: '入力して新しい報告を送信。',
      fb_replay_view: '表示', fb_replay_load_failed: 'リプレイ読み込み失敗', fb_replay_unavailable: 'リプレイは存在しないか期限切れです',
      fb_admin_prefix: '管理者', fb_request_failed: 'リクエスト失敗',
      feedback_center: 'フィードバックセンター', bug_tab: 'バグ', suggestion_tab: '提案', internal_tab: '内部', internal_kind: '内部フィードバック', project_subtitle: 'バグと提案',
      project_copy: 'バグを報告したり、今後の更新を提案できます。',
      status: '状態', all_status: 'すべて', sort: '並び替え', sort_priority: '優先度',
      results: '{0} 件',
      sort_recent: '新しい順', sort_votes: '投票順', sort_updated: '更新順',
      prev: '前へ', next: '次へ', empty: '報告はまだありません。', loading: '読み込み中…',
      select_detail: '報告を選択してください。', new_report: '新規報告',
      back_list: '一覧へ戻る', back_game: 'ゲームへ戻る', votes: '票', vote: '投票',
      remove_vote: '投票を取り消す', comments: 'コメント',
      login_hint: '投稿・コメント・投票にはログインが必要です。',
      guest_more: 'ログインすると全 {0} 件のコメントを表示できます。',
      comment_placeholder: 'コメント…', send: '送信', edit: '編集', delete: '削除',
      save: '保存', cancel: 'キャンセル', private_title: '非公開補足（投稿者とスタッフのみ）',
      private_placeholder: '非公開情報…', staff_zone: 'スタッフ管理', reason: '公開理由',
      priority: '優先度', pin: '固定', unpin: '固定解除', hide_issue: '非表示',
      unhide_issue: '復元', hide_comment: 'コメント非表示', unhide_comment: 'コメント復元',
      internal_note: '内部メモ', history: '履歴', deleted_player: '削除されたプレイヤー',
      author: '投稿者', updated: '更新 {0}', login: 'ログイン', account_label: 'アカウント',
      messages_mark_all_read: 'すべて既読',
      mark_read: '既読にする', notification_status: '状態', notification_comment: '新着コメント',
      notification_private: '非公開補足', notification_reopen: '未修正の報告',
      watch: 'ウォッチ', watched: 'ウォッチ中', rail_details: '詳細', rail_version: 'ゲームバージョン',
      rail_fix_version: '修正バージョン', rail_tags: 'タグ', rail_related: '関連問題',
      rail_watchers: 'ウォッチ人数', rail_replay: 'リプレイ',
      ago_now: 'たった今', ago_min: '{0}分前', ago_hour: '{0}時間前', ago_day: '{0}日前',
      ago_week: '{0}週間前', ago_month: '{0}か月前',
      report: '通報', report_comment: 'コメントを通報', report_title: '通報',
      submit_report: '送信', replay_hint: 'リプレイID：{0}', need_login: 'ログインしてください。',
      own_issue: '自分の報告には投票できません',
      guest_notice: 'ゲストは閲覧のみ可能です。',
      report_cat_abusive_language: '不適切な言葉', report_cat_sexual_content: '性的コンテンツ',
      report_cat_spam: 'スパム', report_cat_privacy_leak: 'プライバシー漏えい',
      report_cat_harassment: '嫌がらせ', report_cat_misleading: '誤解を招く',
      report_cat_duplicate: '重複', report_cat_other: 'その他',
      bug_status: { new: '未確認', needs_info: '情報不足', confirmed: '確認済み', in_progress: '修正中', fixed: '修正済み', duplicate: '重複', unreproducible: '再現不可', by_design: '仕様', invalid: '無効' },
      suggestion_status: { new: '未審査', under_review: '審査中', accepted: '採用', partially_accepted: '一部採用', planned: '計画済み', rejected: '却下', duplicate: '重複' },
      internal_status: { new: '未処理', needs_info: '情報待ち', in_progress: '処理中', fixed: '完了', duplicate: '重複', invalid: '無効' },
    },
  };

  const state = {
    kind: 'bug',
    status: '',
    search: '',
    sort: 'priority',
    page: 1,
    pages: 1,
    issues: [],
    detail: null,
    account: null,
    isStaff: false,
    authorUnread: 0,
    staffUnread: 0,
    watcherUnread: 0,
    notifications: [],
    notificationsLoaded: false,
    accountOpen: false,
    reportContext: null,
  };

  /* 管理员/申诉是与 bug/建议列表并列的独立视图（/feedback-center/appeal），
     自主页反馈弹窗迁入：线程/消息接口同源，历史对话直接可见。 */
  let appealViewActive = false;
  const fbState = { is_staff: false, unread_count: 0, threads: [], messages: [], thread: null, replay: null };
  let fbActiveTab = 'send';
  let fbActiveThreadId = null;
  let fbStaffView = false;
  const fbCollapsedGroups = { open: false, pending: false, closed: true };

  const VOTABLE = {
    bug: new Set(['new', 'needs_info', 'confirmed', 'in_progress']),
    suggestion: new Set(['new', 'under_review']),
  };

  /* 已收口状态（投票已关闭、无需玩家再跟进）：列表行整体降对比（Mojira 对已解决问题的处理）。 */
  const CLOSED_STATUS = {
    bug: new Set(['fixed', 'duplicate', 'unreproducible', 'by_design', 'invalid']),
    suggestion: new Set(['accepted', 'planned', 'rejected', 'duplicate']),
    internal: new Set(['fixed', 'duplicate', 'invalid']),
  };

  const COMMENT_ICON = '<svg class="fc-row-cicon" viewBox="0 0 16 16" aria-hidden="true">' +
    '<path d="M2.75 2.5h10.5c.69 0 1.25.56 1.25 1.25v6.5c0 .69-.56 1.25-1.25 1.25H8.53l-3.4 2.34a.5.5 0 0 1-.78-.41V11.5h-1.6A1.25 1.25 0 0 1 1.5 10.25v-6.5c0-.69.56-1.25 1.25-1.25z"/></svg>';

  const REPORT_CATEGORIES = [
    'abusive_language', 'sexual_content', 'spam', 'privacy_leak', 'harassment',
    'misleading', 'duplicate', 'other',
  ];

  function lang() {
    try {
      if (typeof currentLang === 'string' && currentLang) return currentLang;
    } catch (_) {}
    try {
      const value = localStorage.getItem('gtn_lang');
      if (value) return value;
    } catch (_) {}
    return 'zh';
  }

  function t(key, fallback) {
    const table = T[lang()] || T.zh;
    if (Object.prototype.hasOwnProperty.call(table, key)) return table[key];
    if (Object.prototype.hasOwnProperty.call(T.zh, key)) return T.zh[key];
    return fallback || key;
  }

  function statusLabel(kind, status) {
    const table = T[lang()] || T.zh;
    const group = table[`${kind}_status`] || T.zh[`${kind}_status`] || {};
    return group[status] || status;
  }

  function kindLabel(kind) {
    if (kind === 'suggestion') return t('suggestion_tab');
    if (kind === 'internal') return t('internal_kind');
    return t('bug_tab');
  }

  function $(id) { return document.getElementById(id); }

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, (ch) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[ch]));
  }

  function fmt(value) {
    try {
      const date = new Date(String(value || '').replace('Z', '+00:00'));
      if (Number.isFinite(date.getTime())) {
        const locale = lang() === 'zh' ? 'zh-CN' : lang() === 'ja' ? 'ja-JP' : lang() === 'fr' ? 'fr-FR' : 'en-US';
        return date.toLocaleString(locale, {
          year: 'numeric', month: '2-digit', day: '2-digit',
          hour: '2-digit', minute: '2-digit', hour12: false,
        });
      }
    } catch (_) {}
    return String(value || '');
  }

  /* 列表行用的相对时间：刚刚 / N 分钟前 / … / 超过一年回退完整日期。 */
  function timeAgo(value) {
    const date = new Date(String(value || '').replace('Z', '+00:00'));
    if (!Number.isFinite(date.getTime())) return String(value || '');
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 0) return fmt(value);
    if (seconds < 60) return t('ago_now');
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return t('ago_min').replace('{0}', String(minutes));
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return t('ago_hour').replace('{0}', String(hours));
    const days = Math.floor(hours / 24);
    if (days < 7) return t('ago_day').replace('{0}', String(days));
    if (days < 30) return t('ago_week').replace('{0}', String(Math.floor(days / 7)));
    if (days < 365) return t('ago_month').replace('{0}', String(Math.floor(days / 30)));
    return fmt(value);
  }

  async function api(path, { method = 'GET', body } = {}) {
    const response = await fetch(path, {
      method,
      credentials: 'same-origin',
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.success === false) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    return data;
  }

  function avatarColor(skin = {}) {
    return String(skin.primary_color || '#FFE763').trim();
  }

  const FC_TITLE_COLORS = Object.freeze({
    admin: '#C0392B', thorn: '#C0392B', bloom: '#1ABC9C',
    root: '#8D6E63', guard: '#2980B9', curse: '#704B87',
    infect: '#7E9638', health: '#2ECC71', elixir: '#F1C40F',
    energy: '#F1C40F', magic: '#3498DB', damage: '#C0392B',
    electric: '#4BA3FF', poison: '#8E44AD', fire: '#E67E22',
    armor: '#95A5A6', precision: '#546E7A', banish: '#6C3483',
    indestructible: '#D4AC0D', critical: '#D4AC0D', primary: '#7EEF6D',
    common: '#7EEF6D', unusual: '#FFE65D', rare: '#4D52E3',
    epic: '#861FDE', legendary: '#DE1F1F', mythic: '#1FDBDE',
    ultra: '#FF2B75', super: '#2BFFA3', omega: '#F329D9',
    eternal: '#EEEEEE', unique: '#555555', milestone: '#5AA469',
    hidden: '#7257A8', neutral: '#7F8C8D', spectator: '#95A5A6',
  });

  function fcTitleColorCss(value) {
    const raw = String(value || '').trim();
    const key = raw.toLowerCase();
    if (FC_TITLE_COLORS[key]) return FC_TITLE_COLORS[key];
    if (/^#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?$/.test(raw)) return raw;
    try {
      if (window.CSS && window.CSS.supports && window.CSS.supports('color', raw)) return raw;
    } catch (_) {}
    return '';
  }

  function normalizeFcTitlePaint(paint, fallbackColor = 'neutral') {
    if (!paint || typeof paint !== 'object') {
      return { kind: 'solid', color: fcTitleColorCss(paint || fallbackColor) || fcTitleColorCss(fallbackColor) };
    }
    const kind = String(paint.kind || '').toLowerCase();
    if (kind === 'solid') {
      return { kind, color: fcTitleColorCss(paint.color) || fcTitleColorCss(fallbackColor) };
    }
    if (kind === 'gradient' || kind === 'rainbow') {
      const colors = (Array.isArray(paint.colors) ? paint.colors : [])
        .map(fcTitleColorCss).filter(Boolean).slice(0, 12);
      if (colors.length < 2) return { kind: 'solid', color: fcTitleColorCss(fallbackColor) };
      const numericAngle = Number(paint.angle);
      const angle = Number.isFinite(numericAngle) ? ((numericAngle % 360) + 360) % 360 : 90;
      return { kind, colors, angle };
    }
    if (kind === 'theme') {
      return {
        kind,
        light: normalizeFcTitlePaint(paint.light, fallbackColor),
        dark: normalizeFcTitlePaint(paint.dark, fallbackColor),
      };
    }
    return { kind: 'solid', color: fcTitleColorCss(fallbackColor) };
  }

  function fcTitlePaintAttrs(rawPaint) {
    const paint = normalizeFcTitlePaint(rawPaint);
    if (paint.kind === 'gradient' || paint.kind === 'rainbow') {
      return {
        cls: 'title-paint-gradient',
        style: `--title-paint-gradient:linear-gradient(${paint.angle}deg,${paint.colors.join(',')});`,
      };
    }
    if (paint.kind === 'theme') {
      return {
        cls: 'title-paint-theme',
        style: `--title-paint-light:${paint.light?.color || fcTitleColorCss('neutral')};` +
          `--title-paint-dark:${paint.dark?.color || fcTitleColorCss('neutral')};`,
      };
    }
    return { cls: 'title-paint-solid', style: `color:${paint.color || fcTitleColorCss('neutral')};` };
  }

  function fcTitleSegments(title = {}) {
    const rawSegments = title?.style?.segments;
    if (Array.isArray(rawSegments) && rawSegments.some((item) => item && item.text != null)) {
      return rawSegments.slice(0, 24).map((item, index) => ({
        id: String(item.id || `s${index + 1}`),
        text: String(item.text || ''),
        paint: normalizeFcTitlePaint(item.paint, title.color || 'neutral'),
      }));
    }
    return [{
      id: 'legacy',
      text: String(title.name || ''),
      paint: normalizeFcTitlePaint({ kind: 'solid', color: title.color || 'neutral' }),
    }];
  }

  function fcTitlesHtml(identity = {}) {
    return (Array.isArray(identity?.equipped_titles) ? identity.equipped_titles : [])
      .filter((title) => title?.name)
      .slice(0, 3)
      .map((title) => fcTitleSegments(title).map((segment, index) => {
        const attrs = fcTitlePaintAttrs(segment.paint);
        const bracket = index === 0 ? '[' : '';
        const close = index === fcTitleSegments(title).length - 1 ? ']' : '';
        return `<span class="fc-title-segment ${attrs.cls}" style="${esc(attrs.style)}">${esc(bracket + segment.text + close)}</span>`;
      }).join('')).join('');
  }

  function fcNameHtml(identity = {}) {
    const name = String(identity?.display_name || identity?.username || '?');
    const paint = identity?.name_style?.paint;
    if (!paint) return esc(name);
    const attrs = fcTitlePaintAttrs(paint);
    return `<span class="fc-name-paint ${attrs.cls}" style="${esc(attrs.style)}">${esc(name)}</span>`;
  }

  function normalizeSkinConfig(raw) {
    const data = (raw && typeof raw === 'object') ? raw : {};
    const color = String(data.primary_color || data.primaryColor || '#FFE763').trim();
    const eyeShape = String(data.eye_shape || data.eyeShape || 'oval').trim().toLowerCase();
    return {
      primary_color: /^#[0-9a-fA-F]{6}$/.test(color) ? color.toUpperCase() : '#FFE763',
      eye_shape: ['oval', 'rectangle', 'diamond', 'hexagon'].includes(eyeShape) ? eyeShape : 'oval',
    };
  }

  function hexToRgb(hex) {
    const text = String(hex || '').replace('#', '');
    if (!/^[0-9a-fA-F]{6}$/.test(text)) return { r: 255, g: 231, b: 99 };
    return {
      r: parseInt(text.slice(0, 2), 16),
      g: parseInt(text.slice(2, 4), 16),
      b: parseInt(text.slice(4, 6), 16),
    };
  }

  function rgbToHex(rgb) {
    return `#${[rgb.r, rgb.g, rgb.b].map((v) =>
      Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('')}`.toUpperCase();
  }

  function deriveSkinBorderColor(color) {
    const rgb = hexToRgb(color);
    return rgbToHex({ r: rgb.r * 0.81, g: rgb.g * 0.81, b: rgb.b * 0.81 });
  }

  function skinLuminance(color) {
    const { r, g, b } = hexToRgb(color);
    const srgb = [r, g, b].map((value) => {
      const channel = value / 255;
      return channel <= 0.03928
        ? channel / 12.92
        : Math.pow((channel + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
  }

  function skinMouthPath() {
    return 'M 20 18 C 36 32 64 32 80 18';
  }

  function skinAvatarHtml(rawSkin) {
    const skin = normalizeSkinConfig(rawSkin);
    const main = skin.primary_color;
    const border = deriveSkinBorderColor(main);
    const eyeShape = skin.eye_shape;
    const inverted = skinLuminance(main) < 0.22 ? ' is-inverted' : '';
    return `<div class="fc-skin-avatar skin-eye-shape-${esc(eyeShape)}${inverted}" style="` +
      `--skin-main:${esc(main)};--skin-border:${esc(border)};` +
      `--skin-look-x:26.9%;--skin-look-y:-39.6%;">` +
      `<div class="skin-eye skin-eye-left"><span class="skin-pupil"></span></div>` +
      `<div class="skin-eye skin-eye-right"><span class="skin-pupil"></span></div>` +
      `<svg class="skin-mouth" viewBox="0 0 100 56" aria-hidden="true" focusable="false">` +
      `<path class="skin-mouth-line" d="${skinMouthPath()}"></path></svg></div>`;
  }

  function userHtml(author) {
    if (!author) return '';
    const name = author.deleted
      ? `<span class="fc-deleted-user">${esc(t('deleted_player'))}</span>`
      : `${fcTitlesHtml(author)}<span class="fc-user-name">${fcNameHtml(author)}</span>`;
    const cls = author.deleted ? 'fc-avatar-mini fc-avatar-deleted' : 'fc-avatar-mini';
    return `<span class="fc-user-line${author.deleted ? ' fc-deleted-user' : ''}">` +
      `<span class="${cls}">${skinAvatarHtml(author.skin)}</span>` +
      `<span class="fc-user-text">${name}</span></span>`;
  }

  function statusToken(status) {
    return String(status || '').replace(/-/g, '_');
  }

  function statusAttr(status) {
    const token = statusToken(status);
    return token ? ` data-fc-status="${esc(token)}"` : '';
  }

  function statusChip(kind, status) {
    const css = statusToken(status);
    return `<span class="fc-status fc-status-${esc(css)}">${esc(statusLabel(kind, status))}</span>`;
  }

  function statusOptions(kind, selected) {
    const keys = kind === 'suggestion'
      ? ['new', 'under_review', 'accepted', 'partially_accepted', 'planned', 'rejected', 'duplicate']
      : kind === 'internal'
        ? ['new', 'needs_info', 'in_progress', 'fixed', 'duplicate', 'invalid']
        : ['new', 'needs_info', 'confirmed', 'in_progress', 'fixed', 'duplicate', 'unreproducible', 'by_design', 'invalid'];
    return keys.map((key) =>
      `<option value="${key}"${key === selected ? ' selected' : ''}>${esc(statusLabel(kind, key))}</option>`,
    ).join('');
  }

  function applyStaticText() {
    const langTable = T[lang()] || T.zh;
    document.title = `${langTable.feedback_center || '反馈中心'} · 荆棘花园`;
    $('fc-brand-sub').textContent = langTable.feedback_center;
    $('fc-open-title').textContent = `${kindLabel(state.kind)}列表`;
    $('fc-status-label').textContent = langTable.status;
    $('fc-sort-label').textContent = langTable.sort;
    $('fc-create').textContent = langTable.new_report;
    $('fc-list-create').textContent = langTable.new_report;
    $('fc-create-title').textContent = langTable.new_report;
    $('fc-prev').textContent = langTable.prev;
    $('fc-next').textContent = langTable.next;
    $('fc-search-label').textContent = '输入筛选';
    $('fc-search').placeholder = '搜索标题与正文…';
    $('fc-status-filter').innerHTML = `<option value="">${esc(langTable.all_status)}</option>${statusOptions(state.kind, state.status)}`;
    $('fc-sort').innerHTML = [
      ['priority', langTable.sort_priority],
      ['recent', langTable.sort_recent],
      ['votes', langTable.sort_votes],
      ['updated', langTable.sort_updated],
    ].map(([value, label]) => `<option value="${value}"${value === state.sort ? ' selected' : ''}>${esc(label)}</option>`).join('');
    $('fc-tab-bug').textContent = t('bug_tab');
    $('fc-tab-suggestion').textContent = t('suggestion_tab');
    $('fc-tab-internal').textContent = t('internal_tab');
    $('feedback-tab-send').textContent = t('fb_send');
    $('feedback-tab-staff').textContent = t('fb_staff');
    $('feedback-tab-handling').textContent = t('fb_handling');
    const catSel = $('feedback-category');
    if (catSel && catSel.options.length >= 3) {
      catSel.options[0].textContent = t('fb_category_account');
      catSel.options[1].textContent = t('fb_category_report');
      catSel.options[2].textContent = t('fb_category_appeal');
    }
    const statusSel = $('feedback-status-select');
    if (statusSel && statusSel.options.length >= 3) {
      statusSel.options[0].textContent = t('fb_status_open');
      statusSel.options[1].textContent = t('fb_status_pending');
      statusSel.options[2].textContent = t('fb_status_closed');
    }
    const fbTitleInput = $('feedback-title-input');
    if (fbTitleInput) fbTitleInput.placeholder = t('fb_title_placeholder');
    const fbReplayInput = $('feedback-replay-id');
    if (fbReplayInput) fbReplayInput.placeholder = t('fb_replay_placeholder');
    const fbMessageInput = $('feedback-message-input');
    if (fbMessageInput) fbMessageInput.placeholder = t('fb_message_placeholder');
    const fbSendBtn = $('btn-feedback-send');
    if (fbSendBtn) fbSendBtn.textContent = t('fb_send_btn');
    updateInboxBadge();
    const internalTab = $('fc-tab-internal');
    if (internalTab) internalTab.hidden = !state.isStaff;
  }

  function updateTabs() {
    $('fc-tab-bug').classList.toggle('is-active', state.kind === 'bug');
    $('fc-tab-suggestion').classList.toggle('is-active', state.kind === 'suggestion');
    $('fc-tab-appeal').classList.toggle('is-active', appealViewActive);
    const internalTab = $('fc-tab-internal');
    if (internalTab) {
      internalTab.classList.toggle('is-active', state.kind === 'internal');
      internalTab.hidden = !state.isStaff;
    }
    $('fc-open-title').textContent = `${kindLabel(state.kind)}列表`;
  }

  async function loadAccount() {
    try {
      const data = await api('/api/auth/me');
      state.account = data.authenticated ? data.user : null;
    } catch (_) {
      state.account = null;
    }
    try {
      const summary = await api('/api/public-feedback/summary');
      state.isStaff = !!summary.is_staff;
      state.authorUnread = Number(summary.author_unread_count || 0);
      state.staffUnread = Number(summary.staff_unread_count || 0);
      state.watcherUnread = Number(summary.watcher_unread_count || 0);
    } catch (_) {}
    renderAccount();
    const canCreate = !!state.account;
    $('fc-create').hidden = !canCreate;
    $('fc-list-create').hidden = !canCreate;
    const internalTab = $('fc-tab-internal');
    if (internalTab) internalTab.hidden = !state.isStaff;
  }

  function renderAccount() {
    const container = $('fc-account');
    if (!state.account) {
      container.innerHTML = `<a class="fc-button fc-button-secondary fc-button-small" href="/" target="_blank" rel="noopener">${esc(t('login'))}</a>`;
      return;
    }
    const user = state.account;
    const unread = state.isStaff
      ? Number(state.staffUnread || 0)
      : Number(state.authorUnread || 0) + Number(state.watcherUnread || 0);
    const badge = unread > 0 ? `<span class="fc-badge">${unread > 99 ? '99+' : unread}</span>` : '';
    container.innerHTML = `<a class="fc-account-chip" href="/feedback-center/messages" title="${esc(t('messages_title'))}">` +
      `<span class="fc-account-avatar-host">${skinAvatarHtml(user.skin)}</span>` +
      `<span class="fc-account-name-wrap">${fcTitlesHtml(user)}<span class="fc-account-name">${fcNameHtml(user)}${badge}</span></span></a>`;
  }

  async function refreshFeedbackUnread() {
    await loadAccount();
    state.notificationsLoaded = false;
    await loadNotifications({ force: true });
  }

  async function markAllNotificationsRead() {
    const ids = [...new Set((state.notifications || [])
      .map((item) => Number(item?.issue?.id || 0))
      .filter((id) => id > 0))];
    for (const issueId of ids) {
      try {
        await api(`/api/public-feedback/issues/${issueId}/read`, { method: 'POST', body: {} });
      } catch (_) {}
    }
    await refreshFeedbackUnread();
    if (window.location.pathname.startsWith('/feedback-center/messages')) {
      await renderMessagesView();
    }
  }

  async function loadNotifications({ force = false } = {}) {
    if (!state.account) return;
    if (!force && state.notificationsLoaded) return;
    try {
      const data = await api('/api/public-feedback/notifications?limit=50');
      state.notifications = Array.isArray(data.items) ? data.items : [];
      state.notificationsLoaded = true;
      renderAccount();
      renderNotifications();
    } catch (_) {}
  }

  function renderNotifications() {
    const panel = $('fc-account-popover');
    if (!panel) return;
    if (!state.account) {
      panel.classList.add('hidden');
      return;
    }
    if (!Array.isArray(state.notifications) || !state.notifications.length) {
      panel.innerHTML = `<div class="fc-account-popover-head">消息</div>` +
        `<div class="fc-account-popover-empty">暂无新消息</div>` +
        `<a class="fc-account-popover-link" href="/" target="_blank" rel="noopener">返回游戏主页</a>`;
      return;
    }
    const items = state.notifications.map((item) => {
      const reason = notificationSummary(item);
      return `<button type="button" class="fc-account-popover-item" data-open-issue="${Number(item.issue?.id || 0)}">` +
        `<strong>${esc(item.issue?.key || '')}</strong>` +
        `<span>${esc(item.issue?.title || '')}</span>` +
        `<small>${esc(notificationTypeText(item))} · ${esc(reason)}</small></button>`;
    }).join('');
    panel.innerHTML = `<div class="fc-account-popover-head">消息</div><div class="fc-account-popover-list">${items}</div>` +
      `<button type="button" class="fc-account-popover-link fc-mark-all-read" data-mark-all-read>${esc(t('messages_mark_all_read'))}</button>` +
      `<a class="fc-account-popover-link" href="/" target="_blank" rel="noopener">返回游戏主页</a>`;
  }

  function notificationTypeText(item) {
    if (item?.type === 'staff') return t('notification_staff');
    if (item?.type === 'watched') return t('notification_watched');
    return t('notification_author');
  }

  /* 消息摘要：动作 + 本地化内容。状态变更用该反馈类型的语言标签（此前显示
     裸 slug 如 "new → fixed"）并带上理由；评论/私密补充给正文前 60 字。 */
  function notificationSummary(item) {
    const brief = String(item?.message || '').trim();
    const excerpt = brief.length > 60 ? `${brief.slice(0, 60)}…` : brief;
    if (item?.action === 'comment') return `${t('notification_comment')}：${excerpt}`;
    if (item?.action === 'private') return `${t('notification_private')}：${excerpt}`;
    if (item?.action === 'reopen_request') return `${t('notification_reopen')}：${excerpt}`;
    const kind = item?.issue?.kind || 'bug';
    const from = item?.from_status ? statusLabel(kind, item.from_status) : '';
    const to = item?.to_status ? statusLabel(kind, item.to_status) : '';
    let text = from ? `${from} → ${to}` : to;
    const reason = String(item?.reason || '').trim();
    if (reason) {
      const short = reason.length > 60 ? `${reason.slice(0, 60)}…` : reason;
      text += `：${short}`;
    }
    return text;
  }

  /* 单条标为已读：读标记推进后该消息即从列表消失（列表是按未读推导的）。 */
  async function markSingleNotificationRead(issueId) {
    if (!Number(issueId)) return;
    try {
      await api(`/api/public-feedback/issues/${Number(issueId)}/read`, { method: 'POST', body: {} });
    } catch (_) {}
    await refreshFeedbackUnread();
    if (window.location.pathname.startsWith('/feedback-center/messages')) {
      await renderMessagesView();
    }
  }

  async function renderMessagesView() {
    const messages = $('fc-messages');
    const toolbar = $('fc-toolbar');
    const split = $('fc-split');
    if (!messages) return;
    messages.classList.remove('hidden');
    toolbar?.classList.add('hidden');
    split?.classList.add('hidden');
    applyStaticText();
    document.title = `${t('messages_title')} · ${t('feedback_center')} · 荆棘花园`;
    if (!state.account) {
      messages.innerHTML = `<div class="fc-messages-head"><h2>${esc(t('messages_title'))}</h2></div>` +
        `<div class="fc-empty"><p>${esc(t('messages_login'))}</p>` +
        `<a class="fc-button fc-button-primary" href="/" target="_blank" rel="noopener">${esc(t('login'))}</a></div>`;
      return;
    }
    messages.innerHTML = `<div class="fc-messages-head"><h2>${esc(t('messages_title'))}</h2>` +
      `<span class="fc-messages-actions">` +
      `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-mark-all-read>${esc(t('messages_mark_all_read'))}</button>` +
      `<a class="fc-button fc-button-secondary fc-button-small" href="${esc(canonicalListPath(state.kind))}">${esc(t('messages_back'))}</a>` +
      `</span></div>` +
      `<div class="fc-messages-list fc-muted">${esc(t('loading'))}</div>`;
    try {
      const data = await api('/api/public-feedback/notifications?limit=100');
      const items = Array.isArray(data.items) ? data.items : [];
      state.notifications = items;
      state.notificationsLoaded = true;
      const list = messages.querySelector('.fc-messages-list');
      if (!items.length) {
        list.className = 'fc-messages-list';
        list.innerHTML = `<div class="fc-account-popover-empty">${esc(t('messages_empty'))}</div>`;
        return;
      }
      list.className = 'fc-messages-list';
      list.innerHTML = items.map((item) => {
        const issue = item.issue || {};
        const typeText = notificationTypeText(item);
        const reason = notificationSummary(item);
        return `<a class="fc-message-item" href="${esc(canonicalIssuePath(issue))}">` +
          `<span class="fc-message-key">${esc(issue.key || `#${issue.id || ''}`)}</span>` +
          `<span><strong class="fc-message-title">${esc(issue.title || '')}</strong>` +
          `<small class="fc-message-meta">${esc(typeText)} · ${esc(reason)}</small></span>` +
          `<time datetime="${esc(item.created_at || '')}">${esc(fmt(item.created_at))}</time>` +
          `<button type="button" class="fc-message-mark" data-mark-read="${Number(issue.id || 0)}" ` +
          `title="${esc(t('mark_read'))}" aria-label="${esc(t('mark_read'))}">×</button></a>`;
      }).join('');
    } catch (err) {
      const list = messages.querySelector('.fc-messages-list');
      if (list) list.innerHTML = `<div class="fc-error">${esc(err.message || 'error')}</div>`;
    }
  }

  function toggleAccountPopover(force) {
    const panel = $('fc-account-popover');
    if (!panel || !state.account) return;
    const open = force === undefined ? !state.accountOpen : !!force;
    state.accountOpen = open;
    panel.classList.toggle('hidden', !open);
    if (open) loadNotifications({ force: true });
    else panel.classList.add('hidden');
  }

  async function loadIssues({ reset = false } = {}) {
    if (reset) state.page = 1;
    const list = $('fc-issue-list');
    if (list) list.innerHTML = `<div class="fc-empty">${esc(t('loading'))}</div>`;
    try {
      const params = new URLSearchParams({
        kind: state.kind, sort: state.sort, page: String(state.page), per_page: '20',
      });
      if (state.status) params.set('status', state.status);
      if (state.search) params.set('q', state.search);
      const data = await api(`/api/public-feedback/issues?${params.toString()}`);
      state.issues = Array.isArray(data.items) ? data.items : [];
      state.pages = Math.max(1, Number(data.pages || 1));
      state.page = Math.max(1, Number(data.page || 1));
      renderIssues();
      $('fc-page').textContent = `${state.page} / ${state.pages}`;
      $('fc-prev').disabled = state.page <= 1;
      $('fc-next').disabled = state.page >= state.pages;
    } catch (err) {
      const target = $('fc-issue-list');
      if (target) target.innerHTML = `<div class="fc-empty">${esc(err.message || t('empty'))}</div>`;
    }
  }

  function renderIssues() {
    const list = $('fc-issue-list');
    if (!state.issues.length) {
      list.innerHTML = `<div class="fc-empty">${esc(t('empty'))}</div>`;
      return;
    }
    list.innerHTML = state.issues.map((issue) => {
      const selected = state.detail && Number(state.detail.id) === Number(issue.id) ? ' is-selected' : '';
      const icon = issue.kind === 'bug'
        ? `<img class="fc-row-icon" src="/static/assets/icons/bug.svg" alt="Bug 图标">`
        : issue.kind === 'internal'
          ? `<span class="fc-row-icon fc-row-icon-internal" aria-hidden="true">内</span>`
          : `<span class="fc-row-icon fc-row-icon-suggestion" aria-hidden="true">✦</span>`;
      const closed = (CLOSED_STATUS[issue.kind] || new Set()).has(issue.status);
      const votes = Number(issue.vote_count || 0);
      const commentTotal = Number(issue.comment_count || 0);
      const counts = votes || commentTotal
        ? `<span class="fc-row-counts">` +
          `${votes ? `<span class="fc-row-votes" title="${esc(t('votes'))}"><i class="fc-caret" aria-hidden="true"></i>${votes}</span>` : ''}` +
          `${commentTotal ? `<span class="fc-row-comments" title="${esc(t('comments'))}">${COMMENT_ICON}${commentTotal}</span>` : ''}` +
          `</span>`
        : '';
      return `<a class="fc-issue-row${selected}${closed ? ' is-resolved' : ''}" href="${esc(canonicalIssuePath(issue))}" data-open-issue="${issue.id}">` +
        `<span class="fc-issue-top">${icon}<span class="fc-issue-key"${statusAttr(issue.status)}>${esc(issue.key || `#${issue.id}`)}</span>` +
        `${issue.pinned ? `<span class="fc-row-pin">${esc(t('pin'))}</span>` : ''}` +
        `<time class="fc-row-time">${esc(timeAgo(issue.updated_at))}</time></span>` +
        `<span class="fc-issue-summary">${esc(issue.title)}</span>` +
        `<span class="fc-issue-status-line">${statusChip(issue.kind, issue.status)}${counts}</span></a>`;
    }).join('');
  }

  async function openIssue(issueId, { replace = false } = {}) {
    try {
      const hiddenQuery = state.kind === 'internal' && state.isStaff ? '?include_hidden=1' : '';
      const data = await api(`/api/public-feedback/issues/${Number(issueId)}${hiddenQuery}`);
      state.detail = data.issue || null;
      state.kind = state.detail.kind;
      const path = canonicalIssuePath(state.detail);
      if (window.location.pathname !== path) {
        if (replace) history.replaceState({}, '', path);
        else history.pushState({}, '', path);
      }
      renderDetail();
      renderIssues();
      // 反馈 #156：以前只有 Staff / 关注者 / 有私密补充的条目才标记已读，作者
      // 自己打开反馈时红点永远不减。这里改成打开就尝试标记（服务端会校验权限，
      // 无权限时静默忽略），标完立刻刷新红点。
      try {
        await api(`/api/public-feedback/issues/${Number(issueId)}/read`, { method: 'POST', body: {} });
      } catch (_) {}
      await refreshFeedbackUnread();
    } catch (err) {
      const detail = $('fc-detail');
      detail.innerHTML = `<div class="fc-empty">${esc(err.message || 'error')}</div>`;
    }
  }

  function closeIssue() {
    state.detail = null;
    const detail = $('fc-detail');
    detail.innerHTML = `<div class="fc-empty"><h2>${esc(t('select_detail'))}</h2></div>`;
    const path = canonicalListPath(state.kind) + listQueryString();
    if (window.location.pathname !== canonicalListPath(state.kind) || window.location.search) {
      history.pushState({}, '', path);
    }
    renderIssues();
  }

  function showFeedbackSplitView() {
    const messages = $('fc-messages');
    const toolbar = $('fc-toolbar');
    const split = $('fc-split');
    messages?.classList.add('hidden');
    toolbar?.classList.remove('hidden');
    split?.classList.remove('hidden');
    $('fc-appeal-pane')?.classList.add('hidden');
    appealViewActive = false;
  }

  function showBrowse() {
    showFeedbackSplitView();
    closeIssue();
  }

  /* —— 管理员/申诉视图（自主页反馈弹窗迁入）：接口与历史对话同源。 —— */
  function fbTimeShort(value) {
    const time = new Date(value);
    if (Number.isNaN(time.getTime())) return String(value || '');
    const pad = (n) => String(n).padStart(2, '0');
    return `${time.getFullYear()}-${pad(time.getMonth() + 1)}-${pad(time.getDate())} ${pad(time.getHours())}:${pad(time.getMinutes())}`;
  }

  function fbNameClass(role) {
    const key = String(role || '').toLowerCase();
    if (key === 'admin') return 'admin-name';
    if (key === 'staff') return 'bloom-name';
    if (key === 'contributor') return 'guard-name';
    if (key === 'sponsor') return 'thorn-name';
    return '';
  }

  function fbStatusLabel(status) {
    const key = String(status || '').toLowerCase();
    if (key === 'closed') return t('fb_status_closed');
    if (key === 'pending') return t('fb_status_pending');
    return t('fb_status_open');
  }

  function fbStaffGroups(items = []) {
    const groups = [
      { key: 'open', label: fbStatusLabel('open'), items: [] },
      { key: 'pending', label: fbStatusLabel('pending'), items: [] },
      { key: 'closed', label: fbStatusLabel('closed'), items: [] },
    ];
    const byKey = Object.fromEntries(groups.map(group => [group.key, group]));
    (Array.isArray(items) ? items : []).forEach(item => {
      const key = ['open', 'pending', 'closed'].includes(String(item.status || '').toLowerCase())
        ? String(item.status || '').toLowerCase()
        : 'open';
      byKey[key].items.push(item);
    });
    return groups;
  }

  function updateInboxBadge() {
    const tabBtn = $('fc-tab-appeal');
    if (!tabBtn) return;
    const count = Number(fbState.unread_count || 0);
    const base = esc(t('fb_tab'));
    tabBtn.innerHTML = count > 0
      ? `${base}<span class="fc-badge">${count > 99 ? '99+' : count}</span>`
      : base;
  }

  async function loadFeedbackSummary() {
    if (!state.account) {
      fbState.is_staff = false;
      fbState.unread_count = 0;
      updateInboxBadge();
      return;
    }
    try {
      const data = await api('/api/feedback/summary');
      fbState.is_staff = !!data.is_staff;
      fbState.unread_count = Number(data.unread_count || 0);
    } catch (_) {}
    updateInboxBadge();
  }

  function renderFeedbackThreads() {
    const list = $('feedback-thread-list');
    if (!list) return;
    const items = Array.isArray(fbState.threads) ? fbState.threads : [];
    if (!state.account) {
      list.innerHTML = `<div class="fc-muted">${esc(t('fb_login_required'))}</div>`;
      return;
    }
    if (!items.length) {
      list.innerHTML = `<div class="fc-muted">${esc(fbStaffView ? t('fb_staff_empty') : t('fb_empty'))}</div>`;
      return;
    }
    const renderItem = (item) => {
      const active = String(item.id) === String(fbActiveThreadId);
      const user = item.user || {};
      const title = item.title || item.last_message || `#${item.id}`;
      const status = fbStatusLabel(item.status);
      const replayRef = Number(item.replay_id) > 0 ? `R-${Number(item.replay_id)}` : '';
      return `
        <button class="feedback-thread-item${active ? ' active' : ''}" type="button" data-feedback-thread="${esc(item.id)}">
          <span class="feedback-thread-title">${item.unread ? '<span class="feedback-dot"></span>' : ''}${esc(title)}</span>
          <span class="feedback-thread-meta">${esc([fbStaffView ? `${user.username || '-'} · ${status}` : status, replayRef, fbTimeShort(item.updated_at || item.created_at || '')].filter(Boolean).join(' · '))}</span>
          <span class="feedback-thread-preview">${esc(item.last_message || '')}</span>
        </button>`;
    };
    if (fbStaffView) {
      list.innerHTML = fbStaffGroups(items).map(group => {
        const collapsed = !!fbCollapsedGroups[group.key];
        const rows = collapsed ? '' : group.items.map(renderItem).join('');
        return `
          <section class="feedback-thread-group feedback-thread-group-${esc(group.key)}${collapsed ? ' collapsed' : ''}">
            <button class="feedback-thread-group-title" type="button" data-feedback-group-toggle="${esc(group.key)}">
              <span class="feedback-thread-group-arrow">${collapsed ? '>' : 'v'}</span>
              <span>${esc(group.label)}</span>
              <span>${esc(group.items.length)}</span>
            </button>
            ${rows || (collapsed ? '' : `<div class="feedback-thread-group-empty">${esc(t('fb_staff_empty'))}</div>`)}
          </section>`;
      }).join('');
      return;
    }
    list.innerHTML = items.map(renderItem).join('');
  }

  function renderFeedbackMessages() {
    const list = $('feedback-message-list');
    if (!list) return;
    if (!state.account) {
      list.innerHTML = `<div class="fc-muted">${esc(t('fb_login_required'))}</div>`;
      return;
    }
    const messages = Array.isArray(fbState.messages) ? fbState.messages : [];
    if (!fbActiveThreadId && !messages.length) {
      list.innerHTML = `<div class="fc-muted">${esc(fbStaffView ? t('fb_select_thread') : t('fb_compose_hint'))}</div>`;
      return;
    }
    const currentUserId = state.account && state.account.id;
    list.innerHTML = '';
    const fragment = document.createDocumentFragment();
    messages.forEach(msg => {
      const self = Number(msg.sender_user_id) === Number(currentUserId);
      const row = document.createElement('div');
      row.className = `feedback-message ${self ? 'self' : 'other'}`;
      const bubble = document.createElement('div');
      bubble.className = 'feedback-bubble';
      const meta = document.createElement('div');
      meta.className = `feedback-sender ${fbNameClass(msg.sender_role)}`;
      const isAdmin = String(msg.sender_role || '').toLowerCase() === 'admin';
      const nameSpan = document.createElement('span');
      nameSpan.textContent = `${isAdmin ? `[${t('fb_admin_prefix')}] ` : ''}${msg.sender_name || (self ? (state.account.username || '') : '-')}`;
      meta.appendChild(nameSpan);
      const timeSpan = document.createElement('span');
      timeSpan.className = 'feedback-message-time';
      timeSpan.textContent = fbTimeShort(msg.created_at);
      meta.appendChild(timeSpan);
      const text = document.createElement('div');
      text.className = 'feedback-text';
      text.textContent = msg.message || '';
      bubble.appendChild(meta);
      bubble.appendChild(text);
      row.appendChild(bubble);
      fragment.appendChild(row);
    });
    list.appendChild(fragment);
    list.scrollTop = list.scrollHeight;
  }

  function normalizedFeedbackReplayId(value) {
    const text = String(value || '').trim().toUpperCase();
    const match = text.match(/^(?:([RP])-)?(\d+)$/);
    if (!match || Number(match[2]) <= 0) return null;
    return match[1] ? `${match[1]}-${Number(match[2])}` : String(Number(match[2]));
  }

  function renderFeedbackReplayPreview() {
    const box = $('feedback-replay-preview');
    if (!box) return;
    const threadReplayId = Number(fbState.thread && fbState.thread.replay_id || 0);
    const replay = fbState.replay;
    const replayId = Number(replay && replay.id || threadReplayId || 0);
    if (!(replayId > 0)) {
      box.innerHTML = '';
      box.classList.add('hidden');
      return;
    }
    const replayPrefix = String(replay && replay.replay_prefix || 'R').toUpperCase() === 'P' ? 'P' : 'R';
    const replayRef = String(replay && replay.replay_ref || `${replayPrefix}-${replayId}`);
    const players = replay && Array.isArray(replay.players) ? replay.players.join(' / ') : '';
    const detail = replay
      ? [fbTimeShort(replay.created_at), replay.mode, players].filter(Boolean).join(' · ')
      : t('fb_replay_unavailable');
    box.innerHTML = `
      <div class="feedback-replay-preview-main"><strong>${esc(replayRef)}</strong>${detail ? ` · ${esc(detail)}` : ''}</div>
      ${replay ? `<button class="fc-button fc-button-secondary fc-button-small" type="button" data-feedback-replay-open="${esc(replayRef)}">${esc(t('fb_replay_view'))}</button>` : ''}
    `;
    box.classList.remove('hidden');
  }

  async function loadFeedbackReplayPreview(replayId, showError = false) {
    const normalized = normalizedFeedbackReplayId(replayId);
    fbState.replay = null;
    if (!normalized) {
      renderFeedbackReplayPreview();
      return false;
    }
    try {
      const data = await api(`/api/replays/${encodeURIComponent(normalized)}`);
      fbState.replay = data.replay || null;
      renderFeedbackReplayPreview();
      return !!fbState.replay;
    } catch (err) {
      renderFeedbackReplayPreview();
      if (showError) {
        const errorBox = $('feedback-error');
        if (errorBox) errorBox.textContent = String(err?.message || t('fb_replay_load_failed'));
      }
      return false;
    }
  }

  function updateFeedbackReplayField() {
    const category = $('feedback-category');
    const input = $('feedback-replay-id');
    const creatingAppeal = !fbActiveThreadId
      && !fbStaffView
      && category
      && category.value === 'appeal';
    if (input) input.classList.toggle('hidden', !creatingAppeal);
    if (!fbActiveThreadId && !creatingAppeal) fbState.replay = null;
    renderFeedbackReplayPreview();
  }

  function renderInbox() {
    const staffTab = $('feedback-tab-staff');
    if (staffTab) staffTab.classList.toggle('hidden', !fbState.is_staff);
    const handlingTab = $('feedback-tab-handling');
    if (handlingTab) handlingTab.classList.toggle('hidden', !fbState.is_staff);
    document.querySelectorAll('#fc-appeal-pane [data-feedback-tab]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.feedbackTab === fbActiveTab);
    });
    fbStaffView = fbActiveTab === 'staff';
    const category = $('feedback-category');
    const titleInput = $('feedback-title-input');
    const statusSelect = $('feedback-status-select');
    if (category) category.classList.toggle('hidden', fbStaffView || !!fbActiveThreadId);
    if (titleInput) titleInput.classList.toggle('hidden', fbStaffView || !!fbActiveThreadId);
    if (statusSelect) statusSelect.classList.toggle('hidden', !fbStaffView || !fbActiveThreadId);
    updateFeedbackReplayField();
    renderFeedbackThreads();
    renderFeedbackMessages();
    updateInboxBadge();
  }

  async function loadFeedbackThreads(staffView = false) {
    if (!state.account) {
      fbState.threads = [];
      fbState.messages = [];
      fbState.thread = null;
      fbState.replay = null;
      renderInbox();
      return;
    }
    try {
      let data;
      if (staffView) {
        const statuses = ['open', 'pending', 'closed'];
        const results = await Promise.all(statuses.map(status =>
          api(`/api/feedback/threads?staff=1&status=${encodeURIComponent(status)}&limit=30`)
        ));
        data = {
          is_staff: results.some(item => item && item.is_staff),
          unread_count: Math.max(...results.map(item => Number(item && item.unread_count || 0)), 0),
          items: results.flatMap(item => Array.isArray(item && item.items) ? item.items : []),
        };
      } else {
        data = await api('/api/feedback/threads?staff=0&limit=50');
      }
      fbState.is_staff = !!data.is_staff;
      fbState.unread_count = Number(data.unread_count || 0);
      fbState.threads = Array.isArray(data.items) ? data.items : [];
      if (!fbActiveThreadId && fbState.threads.length && staffView) {
        fbActiveThreadId = fbState.threads[0].id;
        await openFeedbackThread(fbActiveThreadId);
        return;
      }
      renderInbox();
    } catch (err) {
      const box = $('feedback-error');
      if (box) box.textContent = String(err?.message || t('fb_request_failed'));
    }
  }

  async function openFeedbackThread(threadId) {
    if (!threadId) return;
    fbActiveThreadId = threadId;
    try {
      const data = await api('/api/feedback/messages/read', {
        method: 'POST',
        body: { thread_id: threadId, limit: 100 },
      });
      fbState.is_staff = !!data.is_staff;
      fbState.unread_count = Number(data.unread_count || 0);
      fbState.messages = Array.isArray(data.messages) ? data.messages : [];
      const thread = data.thread || {};
      fbState.thread = thread;
      fbState.replay = null;
      const statusSelect = $('feedback-status-select');
      if (statusSelect && thread.status) statusSelect.value = thread.status;
      renderInbox();
      if (thread.replay_id) await loadFeedbackReplayPreview(thread.replay_id);
    } catch (err) {
      const box = $('feedback-error');
      if (box) box.textContent = String(err?.message || t('fb_request_failed'));
    }
  }

  async function sendFeedbackMessage() {
    const input = $('feedback-message-input');
    const text = (input?.value || '').trim();
    const box = $('feedback-error');
    if (box) box.textContent = '';
    if (!state.account) {
      if (box) box.textContent = t('fb_login_required');
      return;
    }
    if (!text) return;
    const payload = { text };
    if (fbActiveThreadId) payload.thread_id = fbActiveThreadId;
    else {
      payload.category = $('feedback-category')?.value || 'other';
      payload.title = ($('feedback-title-input')?.value || '').trim();
      if (payload.category === 'appeal') payload.replay_id = ($('feedback-replay-id')?.value || '').trim();
    }
    try {
      const data = await api('/api/feedback/send', { method: 'POST', body: payload });
      if (input) input.value = '';
      fbActiveThreadId = data.thread?.id || data.thread_id || fbActiveThreadId;
      fbState.is_staff = !!data.is_staff;
      fbState.unread_count = Number(data.unread_count || 0);
      fbState.messages = Array.isArray(data.messages) ? data.messages : [];
      fbState.thread = data.thread || fbState.thread;
      await loadFeedbackThreads(fbStaffView);
      if (fbActiveThreadId) await openFeedbackThread(fbActiveThreadId);
      if (box) box.textContent = t('fb_sent');
    } catch (err) {
      if (box) box.textContent = String(err?.message || t('fb_request_failed'));
    }
  }

  async function updateFeedbackStatus() {
    if (!fbActiveThreadId || !fbState.is_staff) return;
    const status = $('feedback-status-select')?.value || 'open';
    try {
      const data = await api('/api/feedback/status', {
        method: 'POST',
        body: { thread_id: fbActiveThreadId, status },
      });
      fbState.messages = Array.isArray(data.messages) ? data.messages : fbState.messages;
      await loadFeedbackThreads(true);
      await openFeedbackThread(fbActiveThreadId);
    } catch (err) {
      const box = $('feedback-error');
      if (box) box.textContent = String(err?.message || t('fb_request_failed'));
    }
  }

  async function renderAppealView() {
    const pane = $('fc-appeal-pane');
    if (!pane) return;
    appealViewActive = true;
    pane.classList.remove('hidden');
    $('fc-toolbar')?.classList.add('hidden');
    $('fc-split')?.classList.add('hidden');
    applyStaticText();
    updateTabs();
    document.title = `${t('fb_tab')} · ${t('feedback_center')} · 荆棘花园`;
    fbActiveTab = fbState.is_staff && fbActiveTab === 'staff' ? 'staff' : 'send';
    fbActiveThreadId = null;
    fbState.thread = null;
    fbState.replay = null;
    if (!state.account) {
      fbState.threads = [];
      fbState.messages = [];
      renderInbox();
      return;
    }
    await loadFeedbackSummary();
    await loadFeedbackThreads(fbStaffView);
  }

  function canonicalIssuePath(issue) {
    const kind = String(issue?.kind || 'bug');
    const id = Number(issue?.id || 0);
    const prefix = kind === 'suggestion' ? 'GS' : kind === 'internal' ? 'GI' : 'GB';
    return `/feedback-center/issues/${prefix}-${id}`;
  }

  function canonicalListPath(kind) {
    const listKind = kind === 'suggestion' ? 'suggestion' : kind === 'internal' ? 'internal' : 'bug';
    return `/feedback-center/${listKind}`;
  }

  function listQueryString() {
    const params = new URLSearchParams();
    if (state.status) params.set('status', state.status);
    if (state.sort && state.sort !== 'priority') params.set('sort', state.sort);
    if (state.search) params.set('q', state.search);
    if (state.page > 1) params.set('page', String(state.page));
    const query = params.toString();
    return query ? `?${query}` : '';
  }

  function issueKeyParts(key) {
    const match = String(key || '').match(/^(GB|GS|GI)-(\d+)$/i);
    if (!match) return null;
    return {
      prefix: match[1].toUpperCase(),
      kind: match[1].toUpperCase() === 'GS' ? 'suggestion' : match[1].toUpperCase() === 'GI' ? 'internal' : 'bug',
      id: Number(match[2]),
    };
  }

  function parseLocationRoute() {
    const path = window.location.pathname.replace(/\/+$/, '') || '/feedback-center/bug';
    const issueMatch = path.match(/^\/feedback-center\/issues\/(GB|GS|GI)-(\d+)$/i);
    if (issueMatch) {
      return {
        view: 'issue',
        kind: String(issueMatch[1]).toUpperCase() === 'GS' ? 'suggestion' : String(issueMatch[1]).toUpperCase() === 'GI' ? 'internal' : 'bug',
        id: Number(issueMatch[2]),
      };
    }
    const kindMatch = path.match(/^\/feedback-center\/(bug|suggestion|internal)$/i);
    if (kindMatch) {
      return {
        view: 'list',
        kind: String(kindMatch[1]).toLowerCase(),
      };
    }
    if (path === '/feedback-center/messages') {
      return { view: 'messages', kind: 'bug' };
    }
    if (path === '/feedback-center/appeal') {
      return { view: 'appeal', kind: 'bug' };
    }
    return { view: 'list', kind: 'bug' };
  }

  async function applyLocationRoute() {
    const route = parseLocationRoute();
    if (route.view === 'messages') {
      await renderMessagesView();
      return;
    }
    if (route.view === 'appeal') {
      await renderAppealView();
      return;
    }
    showFeedbackSplitView();
    if (route.view === 'issue') {
      state.kind = route.kind;
      applyStaticText();
      updateTabs();
      await openIssue(route.id, { replace: true });
      await loadIssues({ reset: true });
      return;
    }
    state.kind = route.kind;
    const query = new URLSearchParams(window.location.search);
    state.status = query.get('status') || '';
    state.search = query.get('q') || '';
    state.sort = query.get('sort') || 'priority';
    state.page = Math.max(1, Number(query.get('page') || 1));
    const search = $('fc-search');
    if (search) search.value = state.search;
    applyStaticText();
    updateTabs();
    state.detail = null;
    const empty = $('fc-detail');
    if (empty) empty.innerHTML = `<div class="fc-empty"><div class="fc-empty-kicker">荆棘花园反馈</div><h2>${esc(t('select_detail'))}</h2></div>`;
    renderIssues();
    await loadIssues();
  }

  function navigateKind(kind) {
    showFeedbackSplitView();
    state.kind = kind === 'suggestion' ? 'suggestion' : kind === 'internal' ? 'internal' : 'bug';
    state.status = '';
    state.search = '';
    state.page = 1;
    state.detail = null;
    const search = $('fc-search');
    if (search) search.value = '';
    const empty = $('fc-detail');
    if (empty) empty.innerHTML = `<div class="fc-empty"><div class="fc-empty-kicker">荆棘花园反馈</div><h2>${esc(t('select_detail'))}</h2></div>`;
    history.pushState({}, '', canonicalListPath(state.kind));
    applyStaticText();
    updateTabs();
    renderIssues();
    loadIssues({ reset: true });
  }

  function renderDetail() {
    const detail = state.detail;
    const container = $('fc-detail');
    const langTable = T[lang()] || T.zh;
    const logged = !!state.account;
    const isAuthor = !!(state.account && detail.author && Number(detail.author.user_id) === Number(state.account.id));
    const voteState = VOTABLE[detail.kind] && VOTABLE[detail.kind].has(detail.status) && !isAuthor;
    const voteCount = Number(detail.vote_count || 0);
    let voteWidget = '';
    if (detail.kind !== 'internal') {
      if (isAuthor) {
        voteWidget = `<span class="fc-vote-pill fc-vote-pill-static">` +
          `<span class="fc-vote-pill-arrow" aria-hidden="true"></span><span class="fc-vote-pill-count">${voteCount}</span>` +
          `<span class="fc-vote-pill-label">${esc(t('votes'))}</span><span class="fc-vote-pill-hint">${esc(t('own_issue'))}</span></span>`;
      } else if (logged) {
        voteWidget = `<button type="button" class="fc-vote-pill${detail.own_vote ? ' has-voted' : ''}" data-action="vote"${voteState ? '' : ' disabled'} title="${esc(detail.own_vote ? t('remove_vote') : t('vote'))}">` +
          `<span class="fc-vote-pill-arrow" aria-hidden="true"></span><span class="fc-vote-pill-count">${voteCount}</span>` +
          `<span class="fc-vote-pill-label">${esc(detail.own_vote ? t('remove_vote') : t('vote'))}</span></button>`;
      } else {
        voteWidget = `<a class="fc-vote-pill" href="/" target="_blank" rel="noopener" title="${esc(t('login'))}">` +
          `<span class="fc-vote-pill-arrow" aria-hidden="true"></span><span class="fc-vote-pill-count">${voteCount}</span>` +
          `<span class="fc-vote-pill-label">${esc(t('vote'))}</span></a>`;
      }
    }

    let privateBlock = '';
    if (detail.can_private) {
      const messages = Array.isArray(detail.private_messages) ? detail.private_messages : [];
      privateBlock = `<section class="fc-section fc-private"><h3>${esc(t('private_title'))}</h3>` +
        messages.map((message) =>
          `<div class="fc-comment"><div class="fc-comment-head">${userHtml(message.sender)}<span class="fc-comment-time">${esc(fmt(message.created_at))}</span></div>` +
          `<div class="fc-comment-body"><div class="fc-comment-text">${esc(message.message)}</div></div></div>`,
        ).join('') +
        `<div class="fc-composer"><textarea id="fc-private-input" maxlength="2000" placeholder="${esc(t('private_placeholder'))}"></textarea>` +
        `<div class="fc-inline-actions"><button type="button" class="fc-button fc-button-primary fc-button-small" data-action="private-send">${esc(t('send'))}</button></div></div></section>`;
    }

    let staffBlock = '';
    if (detail.is_staff) {
      const notes = Array.isArray(detail.staff_notes) ? detail.staff_notes : [];
      staffBlock = `<section class="fc-section fc-staff"><h3>${esc(t('staff_zone'))}</h3>` +
        `<label>${esc(t('status'))}<select id="fc-admin-status">${statusOptions(detail.kind, detail.status)}</select></label>` +
        `<label>${esc(t('reason'))}<input id="fc-admin-reason" maxlength="500"></label>` +
        `<div class="fc-inline-actions"><button type="button" class="fc-button fc-button-primary fc-button-small" data-action="admin-status">${esc(t('save'))}</button></div>` +
        `<label>${esc(t('priority'))}<select id="fc-admin-priority">${[0, 1, 2, 3, 4, 5].map((v) => `<option value="${v}"${Number(detail.priority) === v ? ' selected' : ''}>${v === 0 ? '—' : v}</option>`).join('')}</select></label>` +
        `<div class="fc-inline-actions">` +
        `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="admin-priority" data-pinned="${detail.pinned ? '1' : '0'}">${esc(detail.pinned ? t('unpin') : t('pin'))}</button>` +
        `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="hide-issue" data-hidden="${detail.visible ? '0' : '1'}">${esc(detail.visible ? t('hide_issue') : t('unhide_issue'))}</button>` +
        `</div><label>${esc(t('internal_note'))}<textarea id="fc-note-input" maxlength="2000"></textarea></label>` +
        `<div class="fc-inline-actions"><button type="button" class="fc-button fc-button-primary fc-button-small" data-action="note-add">${esc(t('send'))}</button></div>` +
        `<label>修复版本<input id="fc-admin-fix" maxlength="80" value="${esc(detail.fix_version || '')}"></label>` +
        `<div class="fc-inline-actions"><button type="button" class="fc-button fc-button-primary fc-button-small" data-action="admin-fix">保存修复版本</button></div>` +
        `<label>标签（空格分隔）<input id="fc-admin-tags" maxlength="400" value="${esc((detail.tags || []).join(' '))}"></label>` +
        `<label>关联问题（如 GS-2）<input id="fc-admin-link-target" maxlength="80"></label>` +
        `<label>关联类型<select id="fc-admin-link-relation">` +
        `<option value="related">相关</option><option value="duplicates">重复</option><option value="fix_caused">由修复引起</option></select></label>` +
        `<div class="fc-inline-actions"><button type="button" class="fc-button fc-button-primary fc-button-small" data-action="admin-tags">保存标签</button>` +
        `<button type="button" class="fc-button fc-button-primary fc-button-small" data-action="admin-link">添加关联</button></div>` +
        (Array.isArray(detail.reopen_requests) && detail.reopen_requests.some((request) => request.status === 'pending')
          ? `<div class="fc-section"><h3>待复核“仍未修复”</h3>` +
            detail.reopen_requests.filter((request) => request.status === 'pending').map((request) =>
              `<div class="fc-comment"><div class="fc-comment-head">${userHtml(request.author)}</div><div class="fc-comment-body">` +
              `<div class="fc-comment-text">${esc(request.message)}</div>` +
              `${request.replay_id ? `<div class="fc-muted">回放：${esc(request.replay_id)}</div>` : ''}` +
              `<div class="fc-inline-actions">` +
              `<button type="button" class="fc-button fc-button-primary fc-button-small" data-action="admin-reopen-request" data-request="${request.id}" data-action-kind="accept">接受并重新开启</button>` +
              `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="admin-reopen-request" data-request="${request.id}" data-action-kind="reject">拒绝</button>` +
              `</div></div></div>`).join('') + `</div>` : '') +
        notes.map((note) => `<div class="fc-comment"><div class="fc-comment-head">${userHtml(note.staff)}</div><div class="fc-comment-body"><div class="fc-comment-text">${esc(note.note)}</div></div></div>`).join('') +
        `</section>`;
    }

    const comments = Array.isArray(detail.comments) ? detail.comments : [];
    const commentTotal = Number(detail.comment_count || comments.length);
    let commentSection = `<section class="fc-section"><h3>${esc(t('comments'))} (${commentTotal})</h3>`;
    if (!comments.length) commentSection += `<p class="fc-muted">—</p>`;
    comments.forEach((comment) => {
      let actions = '';
      if (comment.editable) {
        actions += `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="comment-edit" data-comment="${comment.id}">${esc(t('edit'))}</button>` +
          `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="comment-delete" data-comment="${comment.id}">${esc(t('delete'))}</button>`;
      }
      if (detail.is_staff) {
        actions += `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="comment-hide" data-comment="${comment.id}" data-hidden="${comment.hidden ? '1' : '0'}">` +
          `${esc(comment.hidden ? t('unhide_comment') : t('hide_comment'))}</button>`;
      }
      if (state.account && comment.author && Number(comment.author.user_id) !== Number(state.account.id)) {
        actions += `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="report-comment" data-comment="${comment.id}" data-author="${comment.author.user_id || ''}">${esc(t('report_comment'))}</button>`;
      }
      // 反馈 #329：回复按钮（登录用户可用）
      if (logged) {
        actions += `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="comment-reply" data-comment="${comment.id}">${esc(t('reply', '回复'))}</button>`;
      }
      const isReply = comment.parent_comment_id != null;
      const replyCls = isReply ? ' fc-comment-reply' : '';
      commentSection += `<div class="fc-comment${replyCls}" data-comment-root="${comment.id}"${isReply ? ` data-parent="${comment.parent_comment_id}"` : ''}>` +
        `<div class="fc-comment-head">${userHtml(comment.author)}<span class="fc-comment-time">${esc(fmt(comment.created_at))}</span></div>` +
        `<div class="fc-comment-body">` +
        `<div class="fc-comment-text" data-comment-text="${comment.id}">${esc(comment.body)}</div>` +
        `<div class="fc-inline-actions">${actions}</div></div></div>`;
    });
    if (detail.guest_comment_truncated) {
      commentSection += `<p class="fc-muted">${esc(t('guest_more', 'Sign in for more').replace('{0}', String(commentTotal)))}</p>`;
    }
    commentSection += logged
      ? `<div class="fc-composer"><textarea id="fc-comment-input" maxlength="1000" placeholder="${esc(t('comment_placeholder'))}"></textarea>` +
        `<div class="fc-inline-actions"><button type="button" class="fc-button fc-button-primary fc-button-small" data-action="comment-send">${esc(t('send'))}</button></div></div>`
      : `<p class="fc-muted">${esc(t('login_hint'))}</p>`;
    commentSection += `</section>`;

    const canReport = state.account
      && detail.kind !== 'internal'
      && detail.author
      && Number(detail.author.user_id) !== Number(state.account.id);
    const history = (Array.isArray(detail.status_history) ? detail.status_history : []).map((entry) => {
      const actor = (entry.actor && entry.actor.username) ? entry.actor.username : t('deleted_player');
      const from = entry.from_status ? statusLabel(detail.kind, entry.from_status) : '—';
      return `<div>${esc(actor)} · ${esc(from)} → ${esc(statusLabel(detail.kind, entry.to_status))}${entry.reason ? `：${esc(entry.reason)}` : ''} · ${esc(fmt(entry.created_at))}</div>`;
    }).join('');

    const watchButton = detail.kind === 'internal'
      ? ''
      : state.account
        ? `<button type="button" class="fc-button fc-button-small ${detail.watching ? 'fc-button-secondary' : 'fc-button-primary'}" data-action="watch">${esc(detail.watching ? t('watched') : t('watch'))}</button>`
        : `<a class="fc-button fc-button-secondary fc-button-small" href="/" target="_blank" rel="noopener">${esc(t('login'))}</a>`;
    const tagsHtml = (Array.isArray(detail.tags) ? detail.tags : []).length
      ? `<div class="fc-tag-list">${(detail.tags || []).map((tag) => `<span class="fc-tag">${esc(tag)}</span>`).join('')}</div>`
      : '<span class="fc-muted">—</span>';
    const relatedHtml = (Array.isArray(detail.related_issues) && detail.related_issues.length)
      ? `<div class="fc-related-list">${detail.related_issues.map((item) => {
          const relationText = { related: '相关', duplicates: '重复', fix_caused: '由修复引起' }[item.relation] || item.relation;
          const unlink = detail.is_staff
            ? `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="admin-unlink" data-link="${item.link_id}">移除关联</button>` : '';
          return `<div class="fc-related-item"><a href="${esc(canonicalIssuePath(item.issue))}" data-open-issue="${item.issue.id}"${statusAttr(item.issue.status)}>${esc(item.issue.key)}</a>` +
            `<span class="fc-muted">${esc(item.issue.title)}</span><span class="fc-tag">${esc(relationText)}</span>${unlink}</div>`;
        }).join('')}</div>`
      : '<span class="fc-muted">—</span>';

    /* 右侧元数据窄栏（Jira Details 面板式）：正文列保持宽，元信息竖排收拢 */
    const rail = `<aside class="fc-detail-rail"><h3>${esc(t('rail_details'))}</h3>` +
      `<div class="fc-rail-item"><span>${esc(t('rail_version'))}</span><strong>${esc(detail.game_version || '—')}</strong></div>` +
      `<div class="fc-rail-item"><span>${esc(t('rail_fix_version'))}</span><strong>${esc(detail.fix_version || '—')}</strong></div>` +
      (detail.kind === 'internal'
        ? ''
        : `<div class="fc-rail-item"><span>${esc(t('rail_watchers'))}</span><strong>${Number(detail.watcher_count || 0)}</strong></div>`) +
      (detail.replay_id
        ? `<div class="fc-rail-item"><span>${esc(t('rail_replay'))}</span><strong title="${esc(t('replay_hint', 'Replay {0}').replace('{0}', detail.replay_id))}">${esc(detail.replay_id)}</strong></div>`
        : '') +
      `<div class="fc-rail-item"><span>${esc(t('rail_tags'))}</span>${tagsHtml}</div>` +
      `<div class="fc-rail-item"><span>${esc(t('rail_related'))}</span>${relatedHtml}</div>` +
      `</aside>`;

    /* 标题下互动条：投票 / 关注 / 举报（投票是第一动作） */
    const actionBar = voteWidget || watchButton || canReport
      ? `<div class="fc-detail-actions">${voteWidget}${watchButton}` +
        `${canReport ? `<button type="button" class="fc-button fc-button-secondary fc-button-small fc-action-report" data-action="report-issue">${esc(t('report'))}</button>` : ''}</div>`
      : '';

    let notFixedBlock = '';
    if (detail.kind === 'bug' && detail.status === 'fixed') {
      if (!state.account) {
        notFixedBlock = `<section class="fc-section fc-not-fixed"><h3>仍未修复？</h3>` +
          `<p class="fc-muted">${esc(t('login_hint'))}</p></section>`;
      } else if (detail.not_fixed_submitted) {
        notFixedBlock = `<section class="fc-section fc-not-fixed"><h3>仍未修复？</h3>` +
          `<p class="fc-muted">已提交“仍未修复”，等待 Staff 复核。</p></section>`;
      } else {
        notFixedBlock = `<section class="fc-section fc-not-fixed"><h3>仍未修复？</h3>` +
          `<textarea id="fc-not-fixed-input" maxlength="1000" placeholder="请说明仍复现的表现，最好附回放 ID…"></textarea>` +
          `<div class="fc-inline-actions"><button type="button" class="fc-button fc-button-primary fc-button-small" data-action="not-fixed-submit">提交仍未修复</button></div></section>`;
      }
    }

    const attachments = Array.isArray(detail.attachments) ? detail.attachments : [];
    const attachmentsHtml = attachments.length
      ? `<div class="fc-issue-attachments">${attachments.map(att =>
          `<img src="${esc(att.url)}" alt="attachment" loading="lazy">`).join('')}</div>`
      : '';

    container.innerHTML = `<div class="fc-detail-nav"><button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="back">← ${esc(t('back_list'))}</button>` +
      `<a href="/" target="_blank" rel="noopener">${esc(t('back_game'))}</a></div>` +
      `<div class="fc-detail-head"><div class="fc-detail-title-wrap">` +
      `<div class="fc-detail-key"><span class="fc-detail-key-value"${statusAttr(detail.status)}>${esc(detail.key)}</span> · ${esc(kindLabel(detail.kind))}</div>` +
      `<h2 class="fc-detail-title">${esc(detail.title)}${statusChip(detail.kind, detail.status)}</h2></div></div>` +
      `<div class="fc-detail-subline">${detail.author ? userHtml(detail.author) : ''}<span>${esc(fmt(detail.created_at))}</span></div>` +
      actionBar +
      attachmentsHtml +
      `<div class="fc-detail-body-grid"><div class="fc-detail-main">` +
      `<div class="fc-body">${esc(detail.body)}</div>` +
      notFixedBlock +
      commentSection + privateBlock +
      `<section class="fc-section"><h3>${esc(t('history'))}</h3><div class="fc-history">${history || '<span class="fc-muted">—</span>'}</div></section>` +
      staffBlock +
      `</div>${rail}</div>`;
  }

  function issueContainer() {
    return $('fc-detail');
  }

  async function vote() {
    if (!state.detail) return;
    try {
      const data = await api(`/api/public-feedback/issues/${state.detail.id}/vote`, { method: 'POST', body: {} });
      state.detail.vote_count = Number(data.vote_count || 0);
      state.detail.own_vote = !!data.voted;
      renderDetail();
    } catch (err) { alert(err.message || t('need_login')); }
  }

  async function commentSend() {
    const input = $('fc-comment-input');
    const body = input ? input.value.trim() : '';
    if (!body || !state.detail) return;
    const parentId = input ? input.dataset.replyTo || null : null;
    try {
      await api(`/api/public-feedback/issues/${state.detail.id}/comments`, { method: 'POST', body: { body, parent_comment_id: parentId ? Number(parentId) : null } });
      await openIssue(state.detail.id);
    } catch (err) { alert(err.message); }
  }

  // 反馈 #329：回复评论——在目标评论下方展开内嵌输入框
  function commentReply(commentId) {
    const root = issueContainer().querySelector(`[data-comment-root="${commentId}"]`);
    if (!root) return;
    // 切换：已打开就关掉
    const existing = root.querySelector('.fc-reply-box');
    if (existing) { existing.remove(); return; }
    document.querySelectorAll('.fc-reply-box').forEach((b) => b.remove());
    const box = document.createElement('div');
    box.className = 'fc-reply-box';
    box.innerHTML = `<textarea class="fc-comment-textarea" id="fc-comment-input" data-reply-to="${commentId}" maxlength="1000" placeholder="${esc(t('reply_placeholder', '回复…'))}" style="width:100%;min-height:48px"></textarea>` +
      `<div class="fc-inline-actions"><button type="button" class="fc-button fc-button-primary fc-button-small" data-action="comment-send">${esc(t('send'))}</button>` +
      `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="comment-reply-cancel">${esc(t('cancel'))}</button></div>`;
    root.querySelector('.fc-comment-body')?.append(box);
    box.querySelector('textarea')?.focus();
  }

  async function privateSend() {
    const input = $('fc-private-input');
    const message = input ? input.value.trim() : '';
    if (!message || !state.detail) return;
    try {
      await api(`/api/public-feedback/issues/${state.detail.id}/private`, { method: 'POST', body: { message } });
      await openIssue(state.detail.id);
    } catch (err) { alert(err.message); }
  }

  function commentEdit(commentId) {
    const root = issueContainer().querySelector(`[data-comment-root="${commentId}"]`);
    if (!root) return;
    const text = root.querySelector('[data-comment-text]');
    const body = text ? text.textContent : '';
    const actions = root.querySelector('.fc-inline-actions');
    if (actions) actions.innerHTML = `<textarea class="fc-comment-textarea" id="fc-comment-editor" maxlength="1000" style="width:100%;min-height:64px">${esc(body)}</textarea>` +
      `<button type="button" class="fc-button fc-button-primary fc-button-small" data-action="comment-save" data-comment="${commentId}">${esc(t('save'))}</button>` +
      `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="comment-cancel">${esc(t('cancel'))}</button>`;
  }

  async function commentSave(commentId) {
    const editor = $('fc-comment-editor');
    const body = editor ? editor.value.trim() : '';
    if (!body) return;
    try {
      await api(`/api/public-feedback/comments/${commentId}`, { method: 'PATCH', body: { body } });
      await openIssue(state.detail.id);
    } catch (err) { alert(err.message); }
  }

  async function commentDelete(commentId) {
    try {
      await api(`/api/public-feedback/comments/${commentId}`, { method: 'DELETE' });
      await openIssue(state.detail.id);
    } catch (err) { alert(err.message); }
  }

  async function commentHide(commentId, hidden) {
    try {
      await api(`/api/public-feedback/admin/comments/${commentId}/hide`, { method: 'POST', body: { hidden: !hidden } });
      await openIssue(state.detail.id);
    } catch (err) { alert(err.message); }
  }

  async function adminStatus() {
    const detail = state.detail;
    if (!detail) return;
    try {
      await api(`/api/public-feedback/admin/issues/${detail.id}/status`, {
        method: 'POST', body: { status: $('fc-admin-status').value, reason: ($('fc-admin-reason') || {}).value || '' },
      });
      await openIssue(detail.id);
    } catch (err) { alert(err.message); }
  }

  async function adminPriority(pinned) {
    const detail = state.detail;
    if (!detail) return;
    try {
      await api(`/api/public-feedback/admin/issues/${detail.id}/priority`, {
        method: 'POST', body: { priority: Number($('fc-admin-priority').value), pinned: !pinned },
      });
      await openIssue(detail.id);
    } catch (err) { alert(err.message); }
  }

  async function hideIssue(hidden) {
    const detail = state.detail;
    if (!detail) return;
    try {
      await api(`/api/public-feedback/admin/issues/${detail.id}/hide`, { method: 'POST', body: { hidden: !hidden } });
      closeIssue();
      await loadIssues();
    } catch (err) { alert(err.message); }
  }

  async function watch() {
    if (!state.detail) return;
    try {
      const data = await api(`/api/public-feedback/issues/${state.detail.id}/watch`, { method: 'POST', body: {} });
      state.detail.watching = !!data.watching;
      state.detail.watcher_count = Number(data.watcher_count || 0);
      renderDetail();
    } catch (err) { alert(err.message || t('need_login')); }
  }

  async function submitNotFixed() {
    const detail = state.detail;
    const input = $('fc-not-fixed-input');
    if (!detail || !input) return;
    const message = input.value.trim();
    if (!message) { alert('请填写仍未修复的说明'); return; }
    const replayMatch = String(message).match(/\b([RP]-?\d{1,10})\b/i);
    try {
      const body = { message };
      if (replayMatch && /^[RP]-\d+$/i.test(replayMatch[1])) body.replay_id = replayMatch[1].toUpperCase();
      await api(`/api/public-feedback/issues/${detail.id}/not-fixed`, { method: 'POST', body });
      await openIssue(detail.id);
    } catch (err) { alert(err.message); }
  }

  async function reviewReopen(requestId, actionKind) {
    const detail = state.detail;
    if (!detail) return;
    try {
      await api(`/api/public-feedback/admin/reopen-requests/${Number(requestId)}`, {
        method: 'POST',
        body: { action: actionKind, reason: '', reopen_status: 'confirmed' },
      });
      await openIssue(detail.id);
    } catch (err) { alert(err.message); }
  }

  async function adminTags() {
    const detail = state.detail;
    if (!detail) return;
    const input = $('fc-admin-tags');
    const tags = (input ? input.value : '').split(/\s+/).map((item) => item.trim()).filter(Boolean);
    try {
      await api(`/api/public-feedback/admin/issues/${detail.id}/tags`, { method: 'POST', body: { tags } });
      await openIssue(detail.id);
    } catch (err) { alert(err.message); }
  }

  async function adminLink() {
    const detail = state.detail;
    if (!detail) return;
    const raw = ($('fc-admin-link-target') || {}).value || '';
    const parts = issueKeyParts(raw.trim());
    if (!parts) { alert('请输入 GB-123 或 GS-123'); return; }
    try {
      await api(`/api/public-feedback/admin/issues/${detail.id}/links`, {
        method: 'POST',
        body: {
          to_issue_id: parts.id,
          relation: ($('fc-admin-link-relation') || {}).value || 'related',
        },
      });
      await openIssue(detail.id);
    } catch (err) { alert(err.message); }
  }

  async function adminUnlink(linkId) {
    try {
      await api(`/api/public-feedback/admin/links/${Number(linkId)}`, { method: 'DELETE' });
      await openIssue(state.detail.id);
    } catch (err) { alert(err.message); }
  }

  async function adminFixVersion() {
    const detail = state.detail;
    if (!detail) return;
    const value = ($('fc-admin-fix') || {}).value || '';
    try {
      await api(`/api/public-feedback/admin/issues/${detail.id}/fix-version`, {
        method: 'POST',
        body: { fix_version: value.trim() },
      });
      await openIssue(detail.id);
    } catch (err) { alert(err.message); }
  }

  async function noteAdd() {
    const detail = state.detail;
    const value = ($('fc-note-input') || {}).value || '';
    if (!detail || !value.trim()) return;
    try {
      await api(`/api/public-feedback/admin/issues/${detail.id}/notes`, { method: 'POST', body: { note: value.trim() } });
      await openIssue(detail.id);
    } catch (err) { alert(err.message); }
  }

  function openCreate() {
    if (!state.account) { alert(t('need_login')); return; }
    const internalOption = Array.from($('fc-create-kind').options)
      .find((option) => option.value === 'internal');
    if (internalOption) internalOption.hidden = !state.isStaff;
    $('fc-create-kind').value = state.kind === 'internal' && state.isStaff
      ? 'internal'
      : (state.kind === 'internal' ? 'bug' : state.kind);
    $('fc-create-title-input').value = '';
    $('fc-create-body').value = '';
    $('fc-create-replay').value = '';
    $('fc-create-error').textContent = '';
    $('fc-create-dialog').showModal();
  }

  /* #235：配图上传（≤3 张，每张 ≤300KB，客户端先拦截超限）。 */
  const createImageIds = [];

  function renderCreateImagePreview() {
    const preview = $('fc-create-images-preview');
    if (!preview) return;
    const inputs = $('fc-create-images');
    if (!inputs) return;
    preview.innerHTML = '';
    createImageIds.forEach((entry, index) => {
      const wrap = document.createElement('span');
      wrap.className = 'fc-attach-item';
      const img = document.createElement('img');
      img.src = entry.url;
      img.alt = entry.name || '';
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'fc-attach-remove';
      remove.textContent = '×';
      remove.title = '移除';
      remove.addEventListener('click', () => {
        createImageIds.splice(index, 1);
        renderCreateImagePreview();
      });
      wrap.appendChild(img);
      wrap.appendChild(remove);
      preview.appendChild(wrap);
    });
    inputs.value = '';
  }

  function bindCreateImageUpload() {
    const inputs = $('fc-create-images');
    if (!inputs) return;
    inputs.addEventListener('change', async () => {
      const errorEl = $('fc-create-error');
      if (errorEl) errorEl.textContent = '';
      const files = [...(inputs.files || [])];
      inputs.value = '';
      for (const file of files) {
        if (createImageIds.length >= 3) {
          if (errorEl) errorEl.textContent = '最多 3 张配图';
          break;
        }
        if (file.size > 300 * 1024) {
          if (errorEl) errorEl.textContent = `${file.name} 超过 300KB，请压缩后再上传`;
          continue;
        }
        const form = new FormData();
        form.append('file', file);
        try {
          const response = await fetch('/api/feedback/attachments', {
            method: 'POST',
            credentials: 'same-origin',
            body: form,
          });
          const data = await response.json().catch(() => ({}));
          if (!response.ok || !data.success) throw new Error(data.error || '上传失败');
          createImageIds.push({ id: data.id, url: data.url, name: file.name });
        } catch (err) {
          if (errorEl) errorEl.textContent = err.message || '上传失败';
          break;
        }
      }
      renderCreateImagePreview();
    });
  }

  async function submitCreate(event) {
    event.preventDefault();
    const title = $('fc-create-title-input').value.trim();
    const body = $('fc-create-body').value.trim();
    const replayId = $('fc-create-replay').value.trim();
    if (!title || !body) { $('fc-create-error').textContent = '标题与内容不能为空'; return; }
    const payload = { kind: $('fc-create-kind').value, title, body };
    if (replayId) payload.replay_id = replayId;
    if (createImageIds.length) payload.attachment_ids = createImageIds.map(entry => entry.id);
    try {
      const data = await api('/api/public-feedback/issues', { method: 'POST', body: payload });
      createImageIds.length = 0;
      renderCreateImagePreview();
      $('fc-create-dialog').close();
      state.kind = data.issue.kind;
      state.status = '';
      applyStaticText();
      await loadIssues({ reset: true });
      await openIssue(data.issue.id);
    } catch (err) { $('fc-create-error').textContent = err.message; }
  }

  function reportTarget(config) {
    state.reportContext = config || null;
    const dialog = $('fc-report-dialog');
    const langTable = T[lang()] || T.zh;
    $('fc-report-title').textContent = langTable.report_title || 'Report';
    $('fc-report-target').textContent = config ? `${config.kind === 'comment' ? t('report_comment') : t('report')} · #${config.id}` : '';
    $('fc-report-category').innerHTML = REPORT_CATEGORIES.map((cat) =>
      `<option value="${cat}">${esc(t(`report_cat_${cat}`, cat))}</option>`).join('');
    $('fc-report-reason').value = '';
    $('fc-report-error').textContent = '';
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  }

  async function submitReport(event) {
    event.preventDefault();
    const context = state.reportContext;
    if (!context) return;
    try {
      await api('/api/report', {
        method: 'POST',
        body: {
          object_type: context.objectType,
          object_id: String(context.id),
          category: $('fc-report-category').value,
          reason_text: $('fc-report-reason').value.trim(),
          target_user_id: context.targetUserId || undefined,
          target_username: context.targetUsername || undefined,
        },
      });
      $('fc-report-dialog').close();
      if (context.commentId) await openIssue(state.detail.id);
    } catch (err) { $('fc-report-error').textContent = err.message; }
  }

  function closeDialog(selector) {
    const dialog = $(selector);
    if (dialog && typeof dialog.close === 'function') dialog.close();
    else if (dialog) dialog.removeAttribute('open');
  }

  // 反馈 #138：手机端软键盘弹出时浏览器会滚动文档露出输入框，键盘收起后背景就留在
  // 滚动后的位置。打开任何对话框时锁定文档滚动，全部关闭后还原原来的滚动位置。
  let feedbackScrollLockY = null;

  function lockFeedbackBackgroundScroll() {
    if (feedbackScrollLockY !== null) return;
    feedbackScrollLockY = window.scrollY || window.pageYOffset || 0;
    document.body.style.top = `-${feedbackScrollLockY}px`;
    document.documentElement.classList.add('fc-scroll-locked');
  }

  function releaseFeedbackBackgroundScroll() {
    if (feedbackScrollLockY === null) return;
    const restoreY = feedbackScrollLockY;
    feedbackScrollLockY = null;
    document.documentElement.classList.remove('fc-scroll-locked');
    document.body.style.top = '';
    window.scrollTo(0, restoreY);
  }

  function bindDialogScrollLock() {
    document.addEventListener('toggle', (event) => {
      const target = event.target;
      if (!target || String(target.tagName || '').toUpperCase() !== 'DIALOG') return;
      if (target.open) {
        lockFeedbackBackgroundScroll();
        return;
      }
      if (!document.querySelector('dialog[open]')) releaseFeedbackBackgroundScroll();
    }, true);
  }

  function bindEvents() {
    let searchTimer = null;
    $('fc-tab-bug').addEventListener('click', () => {
      navigateKind('bug');
    });
    $('fc-tab-suggestion').addEventListener('click', () => {
      navigateKind('suggestion');
    });
    $('fc-tab-appeal').addEventListener('click', () => {
      history.pushState({}, '', '/feedback-center/appeal');
      void renderAppealView();
    });
    $('feedback-tab-handling').addEventListener('click', () => {
      window.open('/handling', '_blank', 'noopener');
    });
    document.querySelectorAll('#fc-appeal-pane [data-feedback-tab]').forEach(btn => {
      btn.addEventListener('click', async () => {
        fbActiveTab = btn.dataset.feedbackTab || 'send';
        fbActiveThreadId = null;
        fbState.messages = [];
        fbState.thread = null;
        fbState.replay = null;
        await loadFeedbackThreads(fbActiveTab === 'staff');
      });
    });
    $('btn-feedback-send').addEventListener('click', sendFeedbackMessage);
    $('feedback-category').addEventListener('change', updateFeedbackReplayField);
    $('feedback-replay-id').addEventListener('change', () => {
      loadFeedbackReplayPreview($('feedback-replay-id').value, true);
    });
    $('feedback-replay-preview').addEventListener('click', (event) => {
      const button = event.target.closest('[data-feedback-replay-open]');
      if (button) {
        window.open(`/?replay=${encodeURIComponent(button.dataset.feedbackReplayOpen)}`, '_blank', 'noopener');
      }
    });
    $('feedback-message-input').addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        sendFeedbackMessage();
      }
    });
    $('feedback-status-select').addEventListener('change', updateFeedbackStatus);
    document.addEventListener('click', (event) => {
      const groupBtn = event.target.closest('#fc-appeal-pane [data-feedback-group-toggle]');
      if (groupBtn) {
        event.preventDefault();
        const key = String(groupBtn.dataset.feedbackGroupToggle || '');
        if (key) {
          fbCollapsedGroups[key] = !fbCollapsedGroups[key];
          renderFeedbackThreads();
        }
        return;
      }
      const threadBtn = event.target.closest('#fc-appeal-pane [data-feedback-thread]');
      if (threadBtn) {
        event.preventDefault();
        openFeedbackThread(threadBtn.dataset.feedbackThread);
      }
    });
    $('fc-search').addEventListener('input', (event) => {
      state.search = event.target.value.trim();
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        history.replaceState({}, '', canonicalListPath(state.kind) + listQueryString());
        loadIssues({ reset: true });
      }, 280);
    });
    $('fc-status-filter').addEventListener('change', (event) => {
      state.status = event.target.value || '';
      history.replaceState({}, '', canonicalListPath(state.kind) + listQueryString());
      loadIssues({ reset: true });
    });
    $('fc-sort').addEventListener('change', (event) => {
      state.sort = event.target.value || 'priority';
      history.replaceState({}, '', canonicalListPath(state.kind) + listQueryString());
      loadIssues({ reset: true });
    });
    $('fc-prev').addEventListener('click', () => {
      if (state.page > 1) {
        state.page -= 1;
        history.replaceState({}, '', canonicalListPath(state.kind) + listQueryString());
        loadIssues();
      }
    });
    $('fc-next').addEventListener('click', () => {
      if (state.page < state.pages) {
        state.page += 1;
        history.replaceState({}, '', canonicalListPath(state.kind) + listQueryString());
        loadIssues();
      }
    });
    $('fc-create').addEventListener('click', openCreate);
    $('fc-list-create').addEventListener('click', openCreate);
    $('fc-create-form').addEventListener('submit', submitCreate);
    $('fc-report-form').addEventListener('submit', submitReport);
    bindCreateImageUpload();
    document.querySelectorAll('[data-close-dialog]').forEach((button) => button.addEventListener('click', () => closeDialog('fc-create-dialog')));
    document.querySelectorAll('[data-close-report]').forEach((button) => button.addEventListener('click', () => closeDialog('fc-report-dialog')));

    document.addEventListener('click', (event) => {
      const markRead = event.target.closest('[data-mark-read]');
      if (markRead) {
        event.preventDefault();
        event.stopPropagation();
        void markSingleNotificationRead(Number(markRead.dataset.markRead || 0));
        return;
      }
      if (event.target.closest('[data-mark-all-read]')) {
        event.preventDefault();
        void markAllNotificationsRead();
        return;
      }
      const issueId = Number(event.target.closest('[data-open-issue]')?.dataset.openIssue || 0);
      if (issueId > 0) {
        event.preventDefault();
        openIssue(issueId);
        return;
      }
      const action = event.target.closest('[data-action]')?.dataset.action;
      if (!action) return;
      if (action === 'back') closeIssue();
      if (action === 'vote') vote();
      if (action === 'comment-send') commentSend();
      if (action === 'comment-reply') commentReply(Number(event.target.closest('[data-action]').dataset.comment));
      if (action === 'comment-reply-cancel') commentReply(Number(event.target.closest('[data-comment-root]')?.dataset.commentRoot || 0));
      if (action === 'comment-edit') commentEdit(Number(event.target.closest('[data-action]').dataset.comment));
      if (action === 'comment-cancel') renderDetail();
      if (action === 'comment-save') commentSave(Number(event.target.closest('[data-action]').dataset.comment));
      if (action === 'comment-delete') commentDelete(Number(event.target.closest('[data-action]').dataset.comment));
      if (action === 'comment-hide') {
        const target = event.target.closest('[data-action]');
        commentHide(Number(target.dataset.comment), target.dataset.hidden === '1');
      }
      if (action === 'private-send') privateSend();
      if (action === 'admin-status') adminStatus();
      if (action === 'admin-priority') adminPriority(event.target.closest('[data-action]').dataset.pinned === '1');
      if (action === 'hide-issue') hideIssue(event.target.closest('[data-action]').dataset.hidden === '1');
      if (action === 'note-add') noteAdd();
      if (action === 'watch') watch();
      if (action === 'not-fixed-submit') submitNotFixed();
      if (action === 'admin-reopen-request') {
        const target = event.target.closest('[data-action]');
        reviewReopen(Number(target.dataset.request), target.dataset.actionKind || 'accept');
      }
      if (action === 'admin-tags') adminTags();
      if (action === 'admin-link') adminLink();
      if (action === 'admin-unlink') adminUnlink(Number(event.target.closest('[data-action]').dataset.link));
      if (action === 'admin-fix') adminFixVersion();
      if (action === 'report-issue') {
        reportTarget({
          id: state.detail.id, kind: 'issue', objectType: 'public_issue',
          targetUserId: state.detail.author?.user_id, targetUsername: state.detail.author?.username,
        });
      }
      if (action === 'report-comment') {
        const target = event.target.closest('[data-action]');
        reportTarget({
          id: Number(target.dataset.comment), kind: 'comment', objectType: 'public_issue_comment',
          commentId: Number(target.dataset.comment),
          targetUserId: Number(target.dataset.author) || undefined,
          targetUsername: '',
        });
      }
    });

    window.addEventListener('popstate', () => {
      applyLocationRoute();
    });
    window.addEventListener('hashchange', () => {
      const legacy = String(location.hash).match(/^#issue-(\d+)$/);
      if (legacy) {
        openIssue(Number(legacy[1]), { replace: true });
        return;
      }
      const kind = String(location.hash).match(/^#(bug|suggestion)$/);
      if (kind) {
        history.replaceState({}, '', canonicalListPath(kind[1]));
        applyLocationRoute();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    bindEvents();
    bindDialogScrollLock();
    await loadAccount();
    await loadNotifications();
    await applyLocationRoute();
    window.addEventListener('focus', () => {
      refreshFeedbackUnread();
      loadFeedbackSummary();
    });
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') refreshFeedbackUnread();
    });
  });

  function loadFeedbackCenterFont() {
    if (!('FontFace' in window) || !document.fonts) return;
    try {
      if (document.fonts.check('14px "Kreadon"')) return;
    } catch (_) {}
    const font = new FontFace(
      'Kreadon',
      "url('/fonts/Kreadon-Regular.subset.woff2?v=3') format('woff2')",
      { weight: '400', style: 'normal' },
    );
    font.load()
      .then((loaded) => {
        if (loaded && document.fonts) document.fonts.add(loaded);
      })
      .catch(() => {});
  }

  if ('requestIdleCallback' in window) {
    requestIdleCallback(loadFeedbackCenterFont, { timeout: 2500 });
  } else {
    window.addEventListener('load', () => {
      setTimeout(loadFeedbackCenterFont, 800);
    }, { once: true });
  }
})();
