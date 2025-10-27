package com.google.firebase.quickstart.trafficlink.services

import com.google.firebase.quickstart.trafficlink.models.*
import java.util.*
import kotlin.math.max
import kotlin.math.min

/**
 * TrafficLinkService implements the core negotiation protocol and dynamic pricing.
 * 
 * Features:
 * - Dynamic pricing based on demand, congestion, and scarcity
 * - Adaptive learning (reinforcement/bandit approach)
 * - Token escrow and settlement
 * - Integration with TrafficOracleService for validation
 */
class TrafficLinkService(
    private val tokenEconomics: TokenEconomics = TokenEconomics(),
    private val pricingParams: PricingParameters = PricingParameters(),
    private val oracleService: TrafficOracleService = TrafficOracleService()
) {
    
    private val activeOffers = mutableMapOf<String, NegotiationOffer>()
    private val completedOffers = mutableListOf<NegotiationOffer>()
    private val systemMetrics = SystemMetrics()
    
    // Track acceptance rate for adaptive pricing
    private var recentAcceptances = 0
    private var recentOffers = 0
    private val adaptiveWindow = 10 // Adjust pricing every 10 offers
    
    /**
     * Calculate dynamic reward amount based on multiple factors.
     * 
     * r(t) depends on:
     * - ΔT (estimated time saved)
     * - Local congestion
     * - Fuel/energy saved
     * - Responder reputation
     * - Scarcity of yielders
     * - Radiation penalty
     * - Sustainability bonus
     */
    fun calculateReward(
        timeSaved: Double,
        congestionLevel: Double,
        fuelSaved: Double,
        responderReputation: Double,
        numAvailableYielders: Int,
        timeInArea: Double
    ): Double {
        // Base reward from time saved
        var reward = timeSaved * pricingParams.baseRewardPerSecond
        
        // Adjust for congestion
        reward *= (1.0 + congestionLevel * pricingParams.congestionMultiplier)
        
        // Add fuel savings
        reward += fuelSaved * pricingParams.fuelSavingsFactor
        
        // Adjust for responder reputation (better reputation = higher reward)
        reward *= (1.0 + responderReputation * pricingParams.reputationWeight)
        
        // Adjust for scarcity (fewer yielders = higher reward)
        val scarcityFactor = if (numAvailableYielders > 0) {
            max(1.0, pricingParams.scarcityMultiplier / numAvailableYielders)
        } else {
            pricingParams.scarcityMultiplier * 2.0
        }
        reward *= scarcityFactor
        
        // Apply bounds
        reward = reward.coerceIn(pricingParams.minReward, pricingParams.maxReward)
        
        return reward
    }
    
    /**
     * Create a new negotiation offer (Initiation phase).
     * Escrows tokens from requester.
     */
    fun createOffer(
        requester: Driver,
        responder: Driver,
        timeSaved: Double,
        congestionLevel: Double,
        fuelSaved: Double,
        numAvailableYielders: Int,
        timeInArea: Double
    ): NegotiationOffer? {
        
        // Calculate reward
        val rewardAmount = calculateReward(
            timeSaved,
            congestionLevel,
            fuelSaved,
            responder.reputation,
            numAvailableYielders,
            timeInArea
        )
        
        // Check if requester has enough tokens
        if (requester.tlkBalance < rewardAmount) {
            return null // Insufficient balance
        }
        
        // Calculate penalties and bonuses
        val radiationPenalty = pricingParams.calculateRadiationPenalty(timeInArea)
        val sustainabilityBonus = if (fuelSaved > 0) {
            fuelSaved * pricingParams.sustainabilityBonusRate
        } else {
            0.0
        }
        
        // Create offer
        val offer = NegotiationOffer(
            offerId = UUID.randomUUID().toString(),
            requesterId = requester.id,
            responderId = responder.id,
            rewardAmount = rewardAmount,
            estimatedTimeSaved = timeSaved,
            congestionLevel = congestionLevel,
            fuelSaved = fuelSaved,
            radiationPenalty = radiationPenalty,
            sustainabilityBonus = sustainabilityBonus,
            expiresAt = Date(System.currentTimeMillis() + pricingParams.offerTimeoutSeconds * 1000L)
        )
        
        // Escrow tokens
        requester.tlkBalance -= rewardAmount
        
        // Store offer
        activeOffers[offer.offerId] = offer
        recentOffers++
        
        return offer
    }
    
    /**
     * Accept an offer (Agreement phase).
     */
    fun acceptOffer(offerId: String, responder: Driver): Boolean {
        val offer = activeOffers[offerId] ?: return false
        
        // Check if offer expired
        if (offer.isExpired()) {
            offer.status = NegotiationStatus.REJECTED
            refundOffer(offer)
            return false
        }
        
        // Check if responder matches
        if (offer.responderId != responder.id) {
            return false
        }
        
        // Accept offer
        offer.status = NegotiationStatus.ACCEPTED
        recentAcceptances++
        
        // Check if we should adjust pricing
        if (recentOffers >= adaptiveWindow) {
            adjustDynamicPricing()
        }
        
        return true
    }
    
    /**
     * Reject an offer.
     */
    fun rejectOffer(offerId: String): Boolean {
        val offer = activeOffers[offerId] ?: return false
        offer.status = NegotiationStatus.REJECTED
        refundOffer(offer)
        
        // Check if we should adjust pricing
        if (recentOffers >= adaptiveWindow) {
            adjustDynamicPricing()
        }
        
        return true
    }
    
    /**
     * Validate and settle an accepted offer (Validation & Settlement phases).
     */
    fun validateAndSettle(
        offerId: String,
        actualTimeSaved: Double,
        safetyMetrics: SafetyMetrics,
        requester: Driver,
        responder: Driver
    ): ValidationResult {
        val offer = activeOffers[offerId] 
            ?: throw IllegalArgumentException("Offer not found")
        
        if (offer.status != NegotiationStatus.ACCEPTED) {
            throw IllegalStateException("Offer not in accepted state")
        }
        
        // Validate with oracle
        val validationResult = oracleService.validateManeuver(
            offer,
            actualTimeSaved,
            safetyMetrics
        )
        
        offer.validationResult = validationResult
        
        if (validationResult.isValid()) {
            // Valid - pay out to responder
            offer.status = NegotiationStatus.SETTLED
            responder.tlkBalance += offer.rewardAmount
            
            // Update reputation
            responder.reputation = min(2.0, responder.reputation + 0.01)
            requester.reputation = min(2.0, requester.reputation + 0.005)
            
            // Record metrics
            systemMetrics.recordNegotiation(
                reward = offer.rewardAmount,
                waitingCost = 0.0,
                penalty = 0.0,
                success = true
            )
        } else {
            // Invalid - refund or dispute
            offer.status = NegotiationStatus.DISPUTED
            refundOffer(offer)
            
            // Penalize reputation
            responder.reputation = max(0.0, responder.reputation - 0.05)
            
            // Record metrics
            systemMetrics.recordNegotiation(
                reward = 0.0,
                waitingCost = 0.0,
                penalty = offer.rewardAmount * 0.1,
                success = false
            )
        }
        
        // Move to completed
        activeOffers.remove(offerId)
        completedOffers.add(offer)
        
        return validationResult
    }
    
    /**
     * Refund escrowed tokens to requester.
     */
    private fun refundOffer(offer: NegotiationOffer) {
        // In real implementation, this would transfer tokens back
        // For now, we just track it in metrics
        systemMetrics.totalPenalties += offer.rewardAmount * 0.01 // Small gas fee
    }
    
    /**
     * Adaptive pricing adjustment based on acceptance rate.
     * Implements reinforcement/bandit learning approach.
     */
    private fun adjustDynamicPricing() {
        val acceptanceRate = if (recentOffers > 0) {
            recentAcceptances.toDouble() / recentOffers
        } else {
            0.0
        }
        
        pricingParams.adjustPricingBasedOnAcceptanceRate(acceptanceRate)
        
        // Reset counters
        recentAcceptances = 0
        recentOffers = 0
    }
    
    /**
     * Get current system metrics.
     */
    fun getSystemMetrics(): SystemMetrics {
        return systemMetrics
    }
    
    /**
     * Get current pricing parameters.
     */
    fun getPricingParameters(): PricingParameters {
        return pricingParams
    }
    
    /**
     * Get token economics state.
     */
    fun getTokenEconomics(): TokenEconomics {
        return tokenEconomics
    }
    
    /**
     * Get all active offers.
     */
    fun getActiveOffers(): List<NegotiationOffer> {
        return activeOffers.values.toList()
    }
    
    /**
     * Clean up expired offers.
     */
    fun cleanupExpiredOffers() {
        val now = Date()
        val expired = activeOffers.values.filter { it.isExpired() }
        expired.forEach { offer ->
            offer.status = NegotiationStatus.REJECTED
            refundOffer(offer)
            activeOffers.remove(offer.offerId)
            completedOffers.add(offer)
        }
    }
}
