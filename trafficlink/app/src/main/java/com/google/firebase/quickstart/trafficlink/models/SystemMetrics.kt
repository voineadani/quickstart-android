package com.google.firebase.quickstart.trafficlink.models

/**
 * Represents system-wide metrics and calculations.
 * 
 * Total system reward:
 * V(t) = Σ[r_i(t) - w_i(t) - p_i(t)]
 * 
 * Net system value:
 * V_net(t) = V(t) - f(A,t) + Sus(t)
 */
data class SystemMetrics(
    var totalRewards: Double = 0.0,         // Σr_i(t)
    var totalWaitingCosts: Double = 0.0,    // Σw_i(t)
    var totalPenalties: Double = 0.0,       // Σp_i(t)
    var radiationPenalty: Double = 0.0,     // f(A,t)
    var sustainabilityBonus: Double = 0.0,  // Sus(t)
    var successfulNegotiations: Int = 0,
    var failedNegotiations: Int = 0,
    var totalTransactions: Int = 0
) {
    /**
     * Calculate total system reward V(t).
     */
    fun calculateSystemReward(): Double {
        return totalRewards - totalWaitingCosts - totalPenalties
    }

    /**
     * Calculate net system value V_net(t).
     */
    fun calculateNetSystemValue(): Double {
        return calculateSystemReward() - radiationPenalty + sustainabilityBonus
    }

    /**
     * Calculate success rate of negotiations.
     */
    fun getSuccessRate(): Double {
        val total = successfulNegotiations + failedNegotiations
        return if (total > 0) successfulNegotiations.toDouble() / total else 0.0
    }

    /**
     * Update metrics after a negotiation completes.
     */
    fun recordNegotiation(
        reward: Double,
        waitingCost: Double,
        penalty: Double,
        success: Boolean
    ) {
        totalRewards += reward
        totalWaitingCosts += waitingCost
        totalPenalties += penalty
        totalTransactions++
        if (success) {
            successfulNegotiations++
        } else {
            failedNegotiations++
        }
    }
}
