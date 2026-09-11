import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class ClassicEquipmentTriggerContractTests(unittest.TestCase):
    def test_classic_equipment_chips_bind_trigger_click_even_before_it_is_triggerable(self):
        """反馈 #72：经典 UI 无法触发装备。

        经典战斗的装备 chip 会在多次渲染之间复用，而“可触发”通常要等到装备
        满一回合才成立。旧实现只在首次绑定时判断 ``is-triggerable``，于是
        芯片永远拿不到点击监听，经典 UI 里装备点不动。
        """

        bind_section = source_between(
            GAME_JS,
            'function attachClassicEquipmentPreviews(',
            'function attachClassicStatusIntros(',
        )
        sync_section = source_between(
            GAME_JS,
            'function updateClassicEquipmentTriggerClasses(',
            'function syncClassicEquipmentChip(',
        )

        # 绑定不再被首次渲染时的 is-triggerable 状态挡住。
        self.assertNotIn("if (chip.classList.contains('is-triggerable')) {", bind_section)
        self.assertIn("chip.addEventListener('click', activate);", bind_section)
        self.assertIn("chip.addEventListener('keydown', (event) => {", bind_section)
        # 点击时才按当前状态校验可触发性与资源。
        self.assertIn("if (!chip.classList.contains('is-triggerable')) return;", bind_section)
        self.assertIn("if (chip.classList.contains('is-trigger-unavailable')) {", bind_section)
        self.assertIn(
            'selectClassicTriggerEquipment(cardInst, getCardDef(cardInst.def_id), event);',
            bind_section,
        )
        # 无障碍属性随每次渲染刷新，键盘也能触发。
        self.assertIn('if (meta.canTrigger) {', sync_section)
        self.assertIn("chip.setAttribute('role', 'button');", sync_section)
        self.assertIn("chip.removeAttribute('tabindex');", sync_section)

    def test_classic_equipment_trigger_state_refreshes_on_every_render(self):
        create_section = source_between(
            GAME_JS,
            'function buildClassicEquipmentChipElement(',
            'function updateClassicEquipmentTriggerClasses(',
        )
        sync_section = source_between(
            GAME_JS,
            'function syncClassicEquipmentChip(',
            'function syncClassicEquipmentRing(',
        )

        self.assertIn('updateClassicEquipmentTriggerClasses(chip, meta);', create_section)
        self.assertIn('updateClassicEquipmentTriggerClasses(chip, meta);', sync_section)


if __name__ == '__main__':
    unittest.main()
