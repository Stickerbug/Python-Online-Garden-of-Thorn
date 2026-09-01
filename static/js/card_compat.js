(function () {
  'use strict';

  var ROOT_CLASS = 'gtn-card-layout-legacy';
  var FLEX_CLASS = 'gtn-card-flex-legacy';
  var CARD_SELECTOR = '.card';
  var raf = window.requestAnimationFrame || function (callback) { return window.setTimeout(callback, 16); };
  var legacyActive = false;
  var flexFallbackActive = false;
  var resizeObserver = null;
  var mutationObserver = null;
  var pendingCards = [];
  var pendingFrame = 0;

  var CARD_METRICS = [
    '--card-border-width',
    '--card-cost-size',
    '--card-cost-border',
    '--card-cost-font',
    '--card-name-font-scale',
    '--card-name-height',
    '--card-art-height',
    '--card-type-font-scale',
    '--card-effect-font-scale',
    '--card-effect-padding-y',
    '--card-effect-padding-x',
    '--card-effect-padding-bottom',
    '--card-flag-font-scale',
    '--card-flag-radius',
    '--card-english-font',
    '--card-english-margin-top',
    '--card-english-padding-x'
  ];

  var EXTRA_RATIOS = {
    '--gtn-card-header-height': 20,
    '--gtn-card-cost-padding-top': 2,
    '--gtn-card-cost-padding-x': 2,
    '--gtn-card-cost-padding-bottom': 0.5,
    '--gtn-card-name-padding-x': 0.5,
    '--gtn-card-english-margin-bottom': 0.2,
    '--gtn-card-english-padding-bottom': 0.9,
    '--gtn-card-art-margin-top': -0.18,
    '--gtn-card-art-margin-bottom': 0.28,
    '--gtn-card-art-radius': 2.2,
    '--gtn-card-art-no-english-margin-bottom': -1.15,
    '--gtn-card-type-padding-y': 0.5,
    '--gtn-card-type-padding-x': 3,
    '--gtn-card-flags-gap': 1.5,
    '--gtn-card-flags-padding-top': 1.5,
    '--gtn-card-flags-padding-x': 3,
    '--gtn-card-flags-padding-bottom': 3,
    '--gtn-card-title-side-space': 20,
    '--gtn-card-title-top': 2
  };

  function supportsContainerCardUnits() {
    try {
      return Boolean(
        window.CSS
        && typeof window.CSS.supports === 'function'
        && window.CSS.supports('container-type', 'inline-size')
        && window.CSS.supports('width', '1cqi')
      );
    } catch (_) {
      return false;
    }
  }

  function elementMatchesCard(element) {
    if (!element || element.nodeType !== 1) return false;
    var matcher = element.matches || element.webkitMatchesSelector || element.msMatchesSelector;
    return typeof matcher === 'function' ? matcher.call(element, CARD_SELECTOR) : false;
  }

  function elementIsConnected(element) {
    if (!element) return false;
    if (typeof element.isConnected === 'boolean') return element.isConnected;
    return Boolean(document.documentElement && document.documentElement.contains(element));
  }

  function nestedFlexCenterWorks() {
    var host = document.body;
    if (!host || !document.createElement) return false;

    var probe = document.createElement('div');
    var left = document.createElement('span');
    var name = document.createElement('span');
    var label = document.createElement('span');
    var right = document.createElement('span');
    probe.setAttribute('aria-hidden', 'true');
    probe.style.cssText = 'position:fixed;left:-10000px;top:0;width:100px;height:20px;display:flex;align-items:center;justify-content:space-between;visibility:hidden;pointer-events:none;overflow:hidden;';
    left.style.cssText = 'display:block;flex:0 0 10px;width:10px;height:10px;';
    right.style.cssText = left.style.cssText;
    name.style.cssText = 'min-width:0;height:20px;flex:1 1 auto;display:flex;align-items:center;justify-content:center;';
    label.style.cssText = 'display:block;width:10px;height:10px;flex:0 0 10px;';
    name.appendChild(label);
    probe.appendChild(left);
    probe.appendChild(name);
    probe.appendChild(right);
    host.appendChild(probe);

    var works = false;
    try {
      var probeRect = probe.getBoundingClientRect();
      var labelRect = label.getBoundingClientRect();
      var probeCenter = probeRect.left + (probeRect.width / 2);
      var labelCenter = labelRect.left + (labelRect.width / 2);
      works = probeRect.width >= 99 && Math.abs(labelCenter - probeCenter) <= 1;
    } catch (_) {
      works = false;
    }
    host.removeChild(probe);
    return works;
  }

  function defaultMetric(card, propertyName) {
    var lang = String(document.documentElement.lang || 'zh').toLowerCase();
    var isStory = card.classList.contains('story-card');
    var ratios = {
      '--card-cost-size': 16,
      '--card-cost-border': 1,
      '--card-cost-font': 9,
      '--card-name-font-scale': 9.5,
      '--card-name-height': 18,
      '--card-art-height': 25,
      '--card-type-font-scale': 6.5,
      '--card-effect-font-scale': 9,
      '--card-effect-padding-y': card.classList.contains('card-has-art') && card.classList.contains('card-no-english') ? 2.9 : 6,
      '--card-effect-padding-x': 2.5,
      '--card-flag-font-scale': 6,
      '--card-flag-radius': 2,
      '--card-english-font': isStory ? 5.75 : 5.55,
      '--card-english-margin-top': -1.55,
      '--card-english-padding-x': 1.45
    };
    if (lang === 'zh') ratios['--card-name-font-scale'] = card.classList.contains('card-name-long-zh') ? 8.9 : 10.5;
    if (lang === 'en' || lang === 'fr' || lang === 'pt' || lang === 'ja') ratios['--card-name-font-scale'] = 8.5;
    if (propertyName === '--card-border-width') return isStory ? 'clamp(1px, 1.3cqi, 1.7px)' : '1.3cqi';
    if (propertyName === '--card-effect-padding-bottom') return '';
    return Object.prototype.hasOwnProperty.call(ratios, propertyName) ? String(ratios[propertyName]) + 'cqi' : '';
  }

  function resolveClamp(value) {
    var match = /^clamp\(\s*(-?(?:\d+|\d*\.\d+))px\s*,\s*(-?(?:\d+|\d*\.\d+))px\s*,\s*(-?(?:\d+|\d*\.\d+))px\s*\)$/i.exec(value);
    if (!match) return value;
    var minimum = parseFloat(match[1]);
    var preferred = parseFloat(match[2]);
    var maximum = parseFloat(match[3]);
    return String(Math.min(maximum, Math.max(minimum, preferred))) + 'px';
  }

  function convertContainerUnits(value, unitPx) {
    var converted = String(value || '').trim().replace(
      /(-?(?:\d+|\d*\.\d+))cqi\b/gi,
      function (_, amount) { return String(parseFloat(amount) * unitPx) + 'px'; }
    );
    return resolveClamp(converted);
  }

  function readMetricTemplate(card) {
    var computed = window.getComputedStyle(card);
    var template = {};
    for (var index = 0; index < CARD_METRICS.length; index += 1) {
      var name = CARD_METRICS[index];
      var value = String(computed.getPropertyValue(name) || '').trim();
      if (!value || value.indexOf('var(') >= 0) value = defaultMetric(card, name);
      template[name] = value;
    }
    return template;
  }

  function applyCardMetrics(card) {
    if (!legacyActive || !card || !elementIsConnected(card)) return;
    var width = card.getBoundingClientRect().width;
    if (!isFinite(width) || width < 20) return;
    if (card.__gtnLegacyCardWidth && Math.abs(card.__gtnLegacyCardWidth - width) < 0.05) return;

    if (!card.__gtnLegacyMetricTemplate) card.__gtnLegacyMetricTemplate = readMetricTemplate(card);
    var unitPx = width / 100;
    var template = card.__gtnLegacyMetricTemplate;
    for (var index = 0; index < CARD_METRICS.length; index += 1) {
      var name = CARD_METRICS[index];
      var converted = convertContainerUnits(template[name], unitPx);
      if (converted) card.style.setProperty(name, converted);
    }
    for (var extraName in EXTRA_RATIOS) {
      if (Object.prototype.hasOwnProperty.call(EXTRA_RATIOS, extraName)) {
        card.style.setProperty(extraName, String(EXTRA_RATIOS[extraName] * unitPx) + 'px');
      }
    }
    card.style.setProperty('--gtn-legacy-card-height', String(width * 88 / 63) + 'px');
    card.__gtnLegacyCardWidth = width;
  }

  function flushCards() {
    pendingFrame = 0;
    var cards = pendingCards.slice();
    pendingCards.length = 0;
    for (var index = 0; index < cards.length; index += 1) {
      var card = cards[index];
      card.__gtnLegacyCardPending = false;
      applyCardMetrics(card);
    }
  }

  function scheduleCard(card) {
    if (!legacyActive || !elementMatchesCard(card)) return;
    if (resizeObserver && !card.__gtnLegacyResizeObserved) {
      card.__gtnLegacyResizeObserved = true;
      resizeObserver.observe(card);
    }
    if (card.__gtnLegacyCardPending) return;
    card.__gtnLegacyCardPending = true;
    pendingCards.push(card);
    if (!pendingFrame) pendingFrame = raf(flushCards);
  }

  function scheduleCardsWithin(root) {
    if (!legacyActive || !root || root.nodeType !== 1) return;
    if (elementMatchesCard(root)) scheduleCard(root);
    if (!root.querySelectorAll) return;
    var cards = root.querySelectorAll(CARD_SELECTOR);
    for (var index = 0; index < cards.length; index += 1) scheduleCard(cards[index]);
  }

  function refreshAllCards() {
    if (!legacyActive) return;
    var cards = document.querySelectorAll(CARD_SELECTOR);
    for (var index = 0; index < cards.length; index += 1) {
      cards[index].__gtnLegacyCardWidth = 0;
      scheduleCard(cards[index]);
    }
  }

  function observeLegacyCards() {
    if (typeof window.ResizeObserver === 'function') {
      resizeObserver = new window.ResizeObserver(function (entries) {
        for (var index = 0; index < entries.length; index += 1) scheduleCard(entries[index].target);
      });
    }
    if (typeof window.MutationObserver === 'function') {
      mutationObserver = new window.MutationObserver(function (records) {
        for (var recordIndex = 0; recordIndex < records.length; recordIndex += 1) {
          var record = records[recordIndex];
          if (record.type === 'attributes') {
            scheduleCardsWithin(record.target);
            continue;
          }
          for (var nodeIndex = 0; nodeIndex < record.addedNodes.length; nodeIndex += 1) {
            scheduleCardsWithin(record.addedNodes[nodeIndex]);
          }
        }
      });
      mutationObserver.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
    } else {
      window.setInterval(refreshAllCards, 1000);
    }
    window.addEventListener('resize', refreshAllCards, false);
    scheduleCardsWithin(document.body);
  }

  function initialize() {
    var containerUnitsWork = supportsContainerCardUnits();
    var flexCenterWorks = nestedFlexCenterWorks();
    flexFallbackActive = !flexCenterWorks;
    legacyActive = !containerUnitsWork || flexFallbackActive;

    window.GTNCardCompatibility = {
      active: legacyActive,
      containerUnits: containerUnitsWork,
      flexCenter: flexCenterWorks,
      refresh: refreshAllCards,
      scheduleCard: scheduleCard
    };
    if (!legacyActive) return;

    document.documentElement.classList.add(ROOT_CLASS);
    if (flexFallbackActive) document.documentElement.classList.add(FLEX_CLASS);
    observeLegacyCards();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, false);
  else initialize();
})();
