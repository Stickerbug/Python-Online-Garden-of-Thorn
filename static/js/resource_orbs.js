(function exposeResourceOrbHelpers(root) {
    'use strict';

    const COMPRESSION_THRESHOLD = 15;

    function wholeNumber(value) {
        const number = Number(value);
        return Number.isFinite(number) ? Math.max(0, Math.floor(number)) : 0;
    }

    function buildChunks(amount, maxChunks = 17, compressionThreshold = COMPRESSION_THRESHOLD) {
        const total = wholeNumber(amount);
        const limit = Math.max(1, wholeNumber(maxChunks));
        const threshold = Math.max(0, wholeNumber(compressionThreshold));
        if (!total) return [];

        if (total <= threshold) {
            if (total <= limit) {
                return Array.from({ length: total }, () => ({ value: 1 }));
            }
            return [
                { value: total - limit + 1, grouped: true },
                ...Array.from({ length: limit - 1 }, () => ({ value: 1 })),
            ];
        }

        const tens = Math.floor(total / 10);
        const ones = total % 10;
        if (tens + ones <= limit) {
            return [
                ...Array.from({ length: tens }, () => ({ value: 10, grouped: true })),
                ...Array.from({ length: ones }, () => ({ value: 1 })),
            ];
        }

        if (ones >= limit) {
            return [
                { value: total - limit + 1, grouped: true },
                ...Array.from({ length: limit - 1 }, () => ({ value: 1 })),
            ];
        }

        const tenSlots = limit - ones;
        const collapsedTens = tens - tenSlots + 1;
        return [
            { value: collapsedTens * 10, grouped: true },
            ...Array.from({ length: tenSlots - 1 }, () => ({ value: 10, grouped: true })),
            ...Array.from({ length: ones }, () => ({ value: 1 })),
        ];
    }

    function buildPreviewChunks(
        current,
        spend,
        displayTotal,
        compressionThreshold = COMPRESSION_THRESHOLD,
        enforceDisplayLimit = false,
    ) {
        const cur = wholeNumber(current);
        const cost = wholeNumber(spend);
        const displayLimit = Math.max(1, wholeNumber(displayTotal));
        const chunkLimit = enforceDisplayLimit
            ? displayLimit
            : Math.max(32, displayLimit * 2);
        const baseChunks = buildChunks(cur, chunkLimit, compressionThreshold)
            .map((chunk) => ({ ...chunk }));
        let spendFromCurrent = Math.min(cur, cost);
        let spentAmount = 0;

        for (let index = baseChunks.length - 1; index >= 0 && spendFromCurrent > 0; index -= 1) {
            const before = wholeNumber(baseChunks[index].value);
            const take = Math.min(before, spendFromCurrent);
            baseChunks[index].value = before - take;
            spentAmount += take;
            spendFromCurrent -= take;
        }

        const remainingChunks = baseChunks.filter((chunk) => wholeNumber(chunk.value) > 0);
        const spendingChunks = buildChunks(spentAmount, chunkLimit, compressionThreshold)
            .map((chunk) => ({ ...chunk, willSpend: true }));
        const missingChunks = buildChunks(
            Math.max(0, cost - cur),
            chunkLimit,
            compressionThreshold,
        )
            .map((chunk) => ({ ...chunk, missing: true, willSpend: true }));
        return remainingChunks.concat(spendingChunks, missingChunks);
    }

    root.GTN_RESOURCE_ORBS = Object.freeze({
        COMPRESSION_THRESHOLD,
        buildChunks,
        buildPreviewChunks,
    });
}(globalThis));
