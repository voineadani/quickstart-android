package com.google.firebase.quickstart.trafficlink.models

/**
 * Tunable parameters for the dynamic pricing algorithm.
 * All terms from the specification are surfaced as configurable parameters.
 */
data class PricingParameters(
    // Base pricing factors
    var baseRewardPerSecond: Double = 0.1,          // Base TLK per second saved
    var congestionMultiplier: Double = 1.5,          // Multiplier for high congestion
    var fuelSavingsFactor: Double = 0.05,            // TLK per unit fuel saved
    var reputationWeight: Double = 0.2,              // Impact of reputation on pricing
    
    // Scarcity and demand factors
    var scarcityMultiplier: Double = 1.0,            // Increases when yielders are scarce
    var demandElasticity: Double = 0.3,              // How fast prices adjust to demand
    
    // Environmental and ethical modifiers
    var radiationPenaltyRate: Double = -0.1,         // f(A,t) - negative per unit time
    var sustainabilityBonusRate: Double = 0.05,      // Sus(t) - positive for eco-behavior
    var loiteringThreshold: Double = 300.0,          // Seconds before radiation penalty kicks in
    
    // Learning parameters for adaptive pricing
    var learningRate: Double = 0.1,                  // How fast to adjust prices
    var acceptanceRateTarget: Double = 0.7,          // Target 70% acceptance rate
    var priceAdjustmentStep: Double = 0.05,          // How much to adjust per iteration
    
    // Safety and legality constraints
    var minReward: Double = 0.5,                     // Minimum reward in TLK
    var maxReward: Double = 50.0,                    // Maximum reward in TLK
    var safetyBuffer: Double = 5.0,                  // Extra time buffer for safety (seconds)
    
    // Waiting cost parameters
    var waitingCostPerSecond: Double = 0.02,         // w(t) - cost per second of waiting
    var penaltyForRefusal: Double = 0.0,             // p(t) - currently no penalty for refusal
    
    // Negotiation timing
    var offerTimeoutSeconds: Int = 30,               // Time limit for accepting offer
    var validationTimeoutSeconds: Int = 60           // Time limit for validation
) {
    /**
     * Adjust pricing based on acceptance rate (reinforcement learning).
     */
    fun adjustPricingBasedOnAcceptanceRate(currentAcceptanceRate: Double) {
        if (currentAcceptanceRate < acceptanceRateTarget) {
            // Too many rejections - increase rewards
            baseRewardPerSecond *= (1.0 + learningRate)
            scarcityMultiplier *= (1.0 + learningRate)
        } else {
            // Too many instant acceptances - decrease rewards
            baseRewardPerSecond *= (1.0 - learningRate * 0.5)
            scarcityMultiplier *= (1.0 - learningRate * 0.5)
        }
        
        // Ensure we stay within bounds
        baseRewardPerSecond = baseRewardPerSecond.coerceIn(0.01, 1.0)
        scarcityMultiplier = scarcityMultiplier.coerceIn(0.5, 3.0)
    }
    
    /**
     * Calculate radiation penalty based on time in area.
     */
    fun calculateRadiationPenalty(timeInAreaSeconds: Double): Double {
        return if (timeInAreaSeconds > loiteringThreshold) {
            radiationPenaltyRate * (timeInAreaSeconds - loiteringThreshold)
        } else {
            0.0
        }
    }
}
