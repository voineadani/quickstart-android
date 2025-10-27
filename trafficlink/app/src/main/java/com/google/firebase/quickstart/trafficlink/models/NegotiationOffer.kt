package com.google.firebase.quickstart.trafficlink.models

import java.util.Date

/**
 * Represents a negotiation offer for right-of-way.
 * 
 * Lifecycle:
 * INITIATED -> ACCEPTED/REJECTED -> VALIDATED -> SETTLED
 */
data class NegotiationOffer(
    val offerId: String,
    val requesterId: String,  // Driver A requesting right-of-way
    val responderId: String,  // Driver B who can yield
    val rewardAmount: Double,  // r(t) - reward in TLK
    val estimatedTimeSaved: Double,  // ΔT in seconds
    val congestionLevel: Double,  // Local congestion factor
    val fuelSaved: Double,  // Estimated fuel/energy saved
    val radiationPenalty: Double,  // f(A,t) - negative value
    val sustainabilityBonus: Double,  // Sus(t) - positive value
    val createdAt: Date = Date(),
    var status: NegotiationStatus = NegotiationStatus.INITIATED,
    var expiresAt: Date = Date(System.currentTimeMillis() + 30000),  // 30 second timeout
    var validationResult: ValidationResult? = null
) {
    /**
     * Calculate the net reward considering all modifiers.
     */
    fun getNetReward(): Double {
        return rewardAmount - radiationPenalty + sustainabilityBonus
    }

    /**
     * Check if the offer has expired.
     */
    fun isExpired(): Boolean {
        return Date().after(expiresAt)
    }
}

/**
 * Negotiation status enum.
 */
enum class NegotiationStatus {
    INITIATED,   // Request created, tokens escrowed
    ACCEPTED,    // Driver B accepted within time limit
    REJECTED,    // Driver B rejected or timed out
    VALIDATED,   // Off-chain validation completed
    SETTLED,     // Tokens paid out or refunded
    DISPUTED     // Validation failed, requires resolution
}

/**
 * Result of off-chain validation by TrafficOracleService.
 */
data class ValidationResult(
    val yieldOccurred: Boolean,
    val maneuverWasSafe: Boolean,
    val timeSavingPositive: Boolean,
    val timestamp: Date = Date(),
    val signature: String = "",  // Oracle signature for attestation
    val details: String = ""
) {
    fun isValid(): Boolean {
        return yieldOccurred && maneuverWasSafe && timeSavingPositive
    }
}
