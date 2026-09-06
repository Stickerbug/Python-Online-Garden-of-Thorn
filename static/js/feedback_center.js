(() => {
  'use strict';

  const T = {
    zh: {
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
      messages_title: '消息', messages_empty: '暂无新消息',
      messages_login: '请先登录账号后查看消息。', messages_back: '返回反馈列表',
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
      suggestion_status: { new: '待审核', under_review: '审核中', accepted: '已采纳', planned: '已规划', rejected: '已拒绝', duplicate: '重复' },
      internal_status: { new: '待处理', needs_info: '需补充', in_progress: '处理中', fixed: '已完成', duplicate: '重复', invalid: '无效' },
    },
    en: {
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
      messages_title: 'Messages', messages_empty: 'No new messages',
      messages_login: 'Sign in to view your messages.', messages_back: 'Back to reports',
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
      suggestion_status: { new: 'New', under_review: 'Under review', accepted: 'Accepted', planned: 'Planned', rejected: 'Declined', duplicate: 'Duplicate' },
      internal_status: { new: 'New', needs_info: 'Needs info', in_progress: 'In progress', fixed: 'Done', duplicate: 'Duplicate', invalid: 'Invalid' },
    },
    fr: {
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
      report: 'Signaler', report_comment: 'Signaler le commentaire', report_title: 'Signaler',
      submit_report: 'Envoyer', replay_hint: 'ID de partie : {0}', need_login: 'Connectez-vous.',
      own_issue: 'Vous ne pouvez pas voter sur votre propre signalement.',
      guest_notice: 'Visiteurs : lecture seule.',
      report_cat_abusive_language: 'Langage abusif', report_cat_sexual_content: 'Contenu sexuel',
      report_cat_spam: 'Spam', report_cat_privacy_leak: 'Vie privée', report_cat_harassment: 'Harcèlement',
      report_cat_misleading: 'Trompeur', report_cat_duplicate: 'Doublon', report_cat_other: 'Autre',
      bug_status: { new: 'Nouveau', needs_info: 'Infos requises', confirmed: 'Confirmé', in_progress: 'Correction', fixed: 'Corrigé', duplicate: 'Doublon', unreproducible: 'Non reproduit', by_design: 'Prévu', invalid: 'Invalide' },
      suggestion_status: { new: 'Nouveau', under_review: 'À l’étude', accepted: 'Accepté', planned: 'Planifié', rejected: 'Refusé', duplicate: 'Doublon' },
      internal_status: { new: 'Nouveau', needs_info: 'Infos requises', in_progress: 'En cours', fixed: 'Terminé', duplicate: 'Doublon', invalid: 'Invalide' },
    },
    ja: {
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
      report: '通報', report_comment: 'コメントを通報', report_title: '通報',
      submit_report: '送信', replay_hint: 'リプレイID：{0}', need_login: 'ログインしてください。',
      own_issue: '自分の報告には投票できません',
      guest_notice: 'ゲストは閲覧のみ可能です。',
      report_cat_abusive_language: '不適切な言葉', report_cat_sexual_content: '性的コンテンツ',
      report_cat_spam: 'スパム', report_cat_privacy_leak: 'プライバシー漏えい',
      report_cat_harassment: '嫌がらせ', report_cat_misleading: '誤解を招く',
      report_cat_duplicate: '重複', report_cat_other: 'その他',
      bug_status: { new: '未確認', needs_info: '情報不足', confirmed: '確認済み', in_progress: '修正中', fixed: '修正済み', duplicate: '重複', unreproducible: '再現不可', by_design: '仕様', invalid: '無効' },
      suggestion_status: { new: '未審査', under_review: '審査中', accepted: '採用', planned: '計画済み', rejected: '却下', duplicate: '重複' },
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

  const VOTABLE = {
    bug: new Set(['new', 'needs_info', 'confirmed', 'in_progress']),
    suggestion: new Set(['new', 'under_review']),
  };

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
      ? ['new', 'under_review', 'accepted', 'planned', 'rejected', 'duplicate']
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
    const internalTab = $('fc-tab-internal');
    if (internalTab) internalTab.hidden = !state.isStaff;
  }

  function updateTabs() {
    $('fc-tab-bug').classList.toggle('is-active', state.kind === 'bug');
    $('fc-tab-suggestion').classList.toggle('is-active', state.kind === 'suggestion');
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
      const typeText = item.type === 'staff'
        ? '待处理请求'
        : item.type === 'watched' ? '关注更新' : '你的反馈更新';
      const reason = item.action === 'reopen_request'
        ? esc(item.message || '')
        : item.action === 'private'
          ? esc(item.message || '')
          : `${esc(item.from_status || '—')} → ${esc(item.to_status || '')}`;
      return `<button type="button" class="fc-account-popover-item" data-open-issue="${Number(item.issue?.id || 0)}">` +
        `<strong>${esc(item.issue?.key || '')}</strong>` +
        `<span>${esc(item.issue?.title || '')}</span>` +
        `<small>${esc(typeText)} · ${esc(reason || '')}</small></button>`;
    }).join('');
    panel.innerHTML = `<div class="fc-account-popover-head">消息</div><div class="fc-account-popover-list">${items}</div>` +
      `<a class="fc-account-popover-link" href="/" target="_blank" rel="noopener">返回游戏主页</a>`;
  }

  function notificationTypeText(item) {
    if (item?.type === 'staff') return t('notification_staff');
    if (item?.type === 'watched') return t('notification_watched');
    return t('notification_author');
  }

  function notificationSummary(item) {
    if (item?.action === 'private') return String(item?.message || '');
    if (item?.action === 'reopen_request') return String(item?.message || '');
    return `${String(item?.from_status || '—')} → ${String(item?.to_status || '')}`;
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
      `<a class="fc-button fc-button-secondary fc-button-small" href="${esc(canonicalListPath(state.kind))}">${esc(t('messages_back'))}</a></div>` +
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
          `<time datetime="${esc(item.created_at || '')}">${esc(fmt(item.created_at))}</time></a>`;
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
      return `<a class="fc-issue-row${selected}" href="${esc(canonicalIssuePath(issue))}" data-open-issue="${issue.id}">` +
        `<span class="fc-issue-top">${icon}<span class="fc-issue-key"${statusAttr(issue.status)}>${esc(issue.key || `#${issue.id}`)}</span></span>` +
        `<span class="fc-issue-summary">${esc(issue.title)}</span>` +
        `<span class="fc-issue-status-line">${statusChip(issue.kind, issue.status)}</span></a>`;
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
      if (state.detail && (state.detail.can_private || state.detail.is_staff || state.detail.watching)) {
        try {
          await api(`/api/public-feedback/issues/${Number(issueId)}/read`, { method: 'POST', body: {} });
        } catch (_) {}
        await refreshFeedbackUnread();
      }
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
  }

  function showBrowse() {
    showFeedbackSplitView();
    closeIssue();
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
    return { view: 'list', kind: 'bug' };
  }

  async function applyLocationRoute() {
    const route = parseLocationRoute();
    if (route.view === 'messages') {
      await renderMessagesView();
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
    let voteButton;
    if (isAuthor) {
      voteButton = `<span class="fc-muted">${esc(t('own_issue'))}</span>`;
    } else if (logged) {
      voteButton = `<button type="button" class="fc-button ${detail.own_vote ? 'fc-button-secondary' : 'fc-button-primary'}" data-action="vote"${voteState ? '' : ' disabled'}>` +
        `${esc(detail.own_vote ? t('remove_vote') : t('vote'))}</button>`;
    } else {
      voteButton = `<a class="fc-button fc-button-secondary fc-button-small" href="/" target="_blank" rel="noopener">${esc(t('login'))}</a>`;
    }

    let privateBlock = '';
    if (detail.can_private) {
      const messages = Array.isArray(detail.private_messages) ? detail.private_messages : [];
      privateBlock = `<section class="fc-section fc-private"><h3>${esc(t('private_title'))}</h3>` +
        messages.map((message) =>
          `<div class="fc-comment"><div>${userHtml(message.sender)}</div><div class="fc-comment-body">` +
          `<div class="fc-muted">${esc(fmt(message.created_at))}</div><div class="fc-comment-text">${esc(message.message)}</div></div></div>`,
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
              `<div class="fc-comment"><div>${userHtml(request.author)}</div><div class="fc-comment-body">` +
              `<div class="fc-comment-text">${esc(request.message)}</div>` +
              `${request.replay_id ? `<div class="fc-muted">回放：${esc(request.replay_id)}</div>` : ''}` +
              `<div class="fc-inline-actions">` +
              `<button type="button" class="fc-button fc-button-primary fc-button-small" data-action="admin-reopen-request" data-request="${request.id}" data-action-kind="accept">接受并重新开启</button>` +
              `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="admin-reopen-request" data-request="${request.id}" data-action-kind="reject">拒绝</button>` +
              `</div></div></div>`).join('') + `</div>` : '') +
        notes.map((note) => `<div class="fc-comment"><div>${userHtml(note.staff)}</div><div class="fc-comment-body"><div class="fc-comment-text">${esc(note.note)}</div></div></div>`).join('') +
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
      commentSection += `<div class="fc-comment" data-comment-root="${comment.id}"><div>${userHtml(comment.author)}</div>` +
        `<div class="fc-comment-body"><div class="fc-muted">${esc(fmt(comment.created_at))}</div>` +
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

    const replay = detail.replay_id
      ? `<p class="fc-muted">${esc(t('replay_hint', 'Replay {0}').replace('{0}', detail.replay_id))}</p>` : '';
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
      ? '<span class="fc-muted">—</span>'
      : state.account
        ? `<button type="button" class="fc-button fc-button-small ${detail.watching ? 'fc-button-secondary' : 'fc-button-primary'}" data-action="watch">${detail.watching ? '已关注' : '关注'}</button>`
        : `<a class="fc-button fc-button-secondary fc-button-small" href="/" target="_blank" rel="noopener">登录后关注</a>`;
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

    const infoPanel = `<section class="fc-info-grid fc-section">` +
      `<div><span>游戏版本</span><strong>${esc(detail.game_version || '—')}</strong></div>` +
      `<div><span>修复版本</span><strong>${esc(detail.fix_version || '—')}</strong></div>` +
      `<div><span>关注</span><strong>${Number(detail.watcher_count || 0)} ${watchButton}</strong></div>` +
      `<div class="fc-info-wide"><span>标签</span>${tagsHtml}</div>` +
      `<div class="fc-info-wide"><span>关联问题</span>${relatedHtml}</div>` +
      `</section>`;

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

    container.innerHTML = `<div class="fc-detail-nav"><button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="back">← ${esc(t('back_list'))}</button>` +
      `<a href="/" target="_blank" rel="noopener">${esc(t('back_game'))}</a></div>` +
      `<div class="fc-detail-head"><div class="fc-detail-title-wrap">` +
      `<div class="fc-detail-key"><span class="fc-detail-key-value"${statusAttr(detail.status)}>${esc(detail.key)}</span> · ${esc(kindLabel(detail.kind))}</div>` +
      `<h2>${esc(detail.title)}</h2></div>` +
      `<div class="fc-detail-side">${statusChip(detail.kind, detail.status)}` +
      `${canReport ? `<button type="button" class="fc-button fc-button-secondary fc-button-small" data-action="report-issue">${esc(t('report'))}</button>` : ''}</div></div>` +
      `<div class="fc-detail-subline">${detail.author ? userHtml(detail.author) : ''}<span>${esc(fmt(detail.created_at))}</span></div>` +
      `${replay}<div class="fc-body">${esc(detail.body)}</div>` +
      infoPanel +
      notFixedBlock +
      `${detail.kind === 'internal' ? '' : `<div class="fc-vote-box"><span class="fc-vote-count">${Number(detail.vote_count || 0)}</span>` +
      `<span class="fc-vote-label">${esc(t('votes'))}</span>${voteButton}</div>`}` +
      commentSection + privateBlock +
      `<section class="fc-section"><h3>${esc(t('history'))}</h3><div class="fc-history">${history || '<span class="fc-muted">—</span>'}</div></section>` +
      staffBlock;
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
    try {
      await api(`/api/public-feedback/issues/${state.detail.id}/comments`, { method: 'POST', body: { body } });
      await openIssue(state.detail.id);
    } catch (err) { alert(err.message); }
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

  async function submitCreate(event) {
    event.preventDefault();
    const title = $('fc-create-title-input').value.trim();
    const body = $('fc-create-body').value.trim();
    const replayId = $('fc-create-replay').value.trim();
    if (!title || !body) { $('fc-create-error').textContent = '标题与内容不能为空'; return; }
    const payload = { kind: $('fc-create-kind').value, title, body };
    if (replayId) payload.replay_id = replayId;
    try {
      const data = await api('/api/public-feedback/issues', { method: 'POST', body: payload });
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

  function bindEvents() {
    let searchTimer = null;
    $('fc-tab-bug').addEventListener('click', () => {
      navigateKind('bug');
    });
    $('fc-tab-suggestion').addEventListener('click', () => {
      navigateKind('suggestion');
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
    document.querySelectorAll('[data-close-dialog]').forEach((button) => button.addEventListener('click', () => closeDialog('fc-create-dialog')));
    document.querySelectorAll('[data-close-report]').forEach((button) => button.addEventListener('click', () => closeDialog('fc-report-dialog')));

    document.addEventListener('click', (event) => {
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
    await loadAccount();
    await loadNotifications();
    await applyLocationRoute();
    window.addEventListener('focus', () => { refreshFeedbackUnread(); });
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
