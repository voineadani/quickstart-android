package com.google.firebase.quickstart.trafficlink.models

/**
 * Represents the tokenomics model for TrafficLink (TLK).
 * 
 * Token: TLK (ERC-20 compatible)
 * Purpose: Compensation medium for yielding right-of-way
 * Exchange: TLK ↔ USDT via constant-product AMM (x·y=k)
 */
data class TokenEconomics(
    val symbol: String = "TLK",
    val totalSupply: Double = 1_000_000.0,
    var tlkReserve: Double = 500_000.0,  // x in constant-product formula
    var usdtReserve: Double = 500_000.0,  // y in constant-product formula
    val k: Double = tlkReserve * usdtReserve  // Constant product
) {
    /**
     * Calculate TLK to USDT exchange rate using constant-product AMM formula.
     * When buying TLK with USDT: x·y=k
     */
    fun getTlkToUsdtRate(): Double {
        return usdtReserve / tlkReserve
    }

    /**
     * Calculate how much USDT is needed to buy a specific amount of TLK.
     */
    fun calculateUsdtForTlk(tlkAmount: Double): Double {
        val newTlkReserve = tlkReserve - tlkAmount
        val newUsdtReserve = k / newTlkReserve
        return newUsdtReserve - usdtReserve
    }

    /**
     * Calculate how much TLK can be bought with a specific amount of USDT.
     */
    fun calculateTlkForUsdt(usdtAmount: Double): Double {
        val newUsdtReserve = usdtReserve + usdtAmount
        val newTlkReserve = k / newUsdtReserve
        return tlkReserve - newTlkReserve
    }

    /**
     * Execute a swap: USDT -> TLK
     */
    fun swapUsdtToTlk(usdtAmount: Double): Double {
        val tlkAmount = calculateTlkForUsdt(usdtAmount)
        usdtReserve += usdtAmount
        tlkReserve -= tlkAmount
        return tlkAmount
    }

    /**
     * Execute a swap: TLK -> USDT
     */
    fun swapTlkToUsdt(tlkAmount: Double): Double {
        val usdtAmount = calculateUsdtForTlk(tlkAmount)
        tlkReserve += tlkAmount
        usdtReserve -= usdtAmount
        return usdtAmount
    }
}
