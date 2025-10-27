package com.google.firebase.quickstart.trafficlink

import androidx.test.ext.junit.runners.AndroidJUnit4
import com.google.firebase.quickstart.trafficlink.models.*
import com.google.firebase.quickstart.trafficlink.services.SafetyMetrics
import com.google.firebase.quickstart.trafficlink.services.TrafficLinkService
import com.google.firebase.quickstart.trafficlink.services.TrafficOracleService
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Instrumented tests for TrafficLink system.
 * Tests core functionality: tokenomics, pricing, negotiation, and validation.
 */
@RunWith(AndroidJUnit4::class)
class TrafficLinkInstrumentedTest {

    private lateinit var trafficLinkService: TrafficLinkService
    private lateinit var oracleService: TrafficOracleService
    private lateinit var tokenEconomics: TokenEconomics
    private lateinit var requester: Driver
    private lateinit var responder: Driver

    @Before
    fun setup() {
        tokenEconomics = TokenEconomics()
        oracleService = TrafficOracleService()
        trafficLinkService = TrafficLinkService(tokenEconomics)
        
        requester = Driver(
            id = "REQ_001",
            name = "Requester",
            tlkBalance = 100.0,
            reputation = 1.0
        )
        
        responder = Driver(
            id = "RESP_001",
            name = "Responder",
            tlkBalance = 50.0,
            reputation = 1.2
        )
    }

    @Test
    fun testTokenEconomics_constantProduct() {
        // Test constant-product AMM formula: x·y=k
        val initialK = tokenEconomics.k
        
        // Swap some USDT for TLK
        val tlkReceived = tokenEconomics.swapUsdtToTlk(1000.0)
        
        // Verify k remains constant
        val newK = tokenEconomics.tlkReserve * tokenEconomics.usdtReserve
        assertEquals(initialK, newK, 0.01)
        
        // Verify we got TLK
        assertTrue(tlkReceived > 0)
    }

    @Test
    fun testTokenEconomics_exchangeRate() {
        val rate = tokenEconomics.getTlkToUsdtRate()
        
        // Rate should be positive
        assertTrue(rate > 0)
        
        // Rate should equal y/x
        val expectedRate = tokenEconomics.usdtReserve / tokenEconomics.tlkReserve
        assertEquals(expectedRate, rate, 0.0001)
    }

    @Test
    fun testDynamicPricing_baseCalculation() {
        val reward = trafficLinkService.calculateReward(
            timeSaved = 30.0,
            congestionLevel = 0.5,
            fuelSaved = 2.0,
            responderReputation = 1.0,
            numAvailableYielders = 5,
            timeInArea = 60.0
        )
        
        // Reward should be positive and within bounds
        assertTrue(reward > 0)
        assertTrue(reward >= trafficLinkService.getPricingParameters().minReward)
        assertTrue(reward <= trafficLinkService.getPricingParameters().maxReward)
    }

    @Test
    fun testDynamicPricing_congestionImpact() {
        val lowCongestionReward = trafficLinkService.calculateReward(
            timeSaved = 30.0,
            congestionLevel = 0.2,
            fuelSaved = 2.0,
            responderReputation = 1.0,
            numAvailableYielders = 5,
            timeInArea = 60.0
        )
        
        val highCongestionReward = trafficLinkService.calculateReward(
            timeSaved = 30.0,
            congestionLevel = 0.8,
            fuelSaved = 2.0,
            responderReputation = 1.0,
            numAvailableYielders = 5,
            timeInArea = 60.0
        )
        
        // High congestion should lead to higher rewards
        assertTrue(highCongestionReward > lowCongestionReward)
    }

    @Test
    fun testDynamicPricing_scarcityImpact() {
        val manyYieldersReward = trafficLinkService.calculateReward(
            timeSaved = 30.0,
            congestionLevel = 0.5,
            fuelSaved = 2.0,
            responderReputation = 1.0,
            numAvailableYielders = 10,
            timeInArea = 60.0
        )
        
        val fewYieldersReward = trafficLinkService.calculateReward(
            timeSaved = 30.0,
            congestionLevel = 0.5,
            fuelSaved = 2.0,
            responderReputation = 1.0,
            numAvailableYielders = 2,
            timeInArea = 60.0
        )
        
        // Fewer yielders should lead to higher rewards
        assertTrue(fewYieldersReward > manyYieldersReward)
    }

    @Test
    fun testNegotiationLifecycle_successfulFlow() {
        // 1. Create offer
        val offer = trafficLinkService.createOffer(
            requester = requester,
            responder = responder,
            timeSaved = 30.0,
            congestionLevel = 0.5,
            fuelSaved = 2.0,
            numAvailableYielders = 5,
            timeInArea = 60.0
        )
        
        assertNotNull(offer)
        assertEquals(NegotiationStatus.INITIATED, offer!!.status)
        
        val initialRequesterBalance = requester.tlkBalance
        
        // 2. Accept offer
        val accepted = trafficLinkService.acceptOffer(offer.offerId, responder)
        assertTrue(accepted)
        
        // 3. Validate and settle
        val safetyMetrics = SafetyMetrics(
            maxDeceleration = 2.5,
            minFollowingDistance = 3.0,
            collisionDetected = false,
            suddenBrakingDetected = false,
            speedLimitViolation = false
        )
        
        val validationResult = trafficLinkService.validateAndSettle(
            offerId = offer.offerId,
            actualTimeSaved = 32.0,
            safetyMetrics = safetyMetrics,
            requester = requester,
            responder = responder
        )
        
        // Verify validation succeeded
        assertTrue(validationResult.isValid())
        
        // Verify tokens transferred
        assertTrue(responder.tlkBalance > 50.0)
        
        // Verify reputation increased
        assertTrue(responder.reputation > 1.2)
    }

    @Test
    fun testNegotiationLifecycle_rejection() {
        val offer = trafficLinkService.createOffer(
            requester = requester,
            responder = responder,
            timeSaved = 30.0,
            congestionLevel = 0.5,
            fuelSaved = 2.0,
            numAvailableYielders = 5,
            timeInArea = 60.0
        )
        
        assertNotNull(offer)
        
        // Reject offer
        val rejected = trafficLinkService.rejectOffer(offer!!.offerId)
        assertTrue(rejected)
        
        // Offer should not be in active list anymore
        assertFalse(trafficLinkService.getActiveOffers().contains(offer))
    }

    @Test
    fun testNegotiationLifecycle_insufficientBalance() {
        // Create driver with insufficient balance
        val poorDriver = Driver(
            id = "POOR_001",
            name = "Poor Driver",
            tlkBalance = 0.5,
            reputation = 1.0
        )
        
        val offer = trafficLinkService.createOffer(
            requester = poorDriver,
            responder = responder,
            timeSaved = 30.0,
            congestionLevel = 0.5,
            fuelSaved = 2.0,
            numAvailableYielders = 5,
            timeInArea = 60.0
        )
        
        // Should fail due to insufficient balance
        assertNull(offer)
    }

    @Test
    fun testValidation_safeManeuver() {
        val offer = NegotiationOffer(
            offerId = "TEST_001",
            requesterId = "REQ_001",
            responderId = "RESP_001",
            rewardAmount = 10.0,
            estimatedTimeSaved = 30.0,
            congestionLevel = 0.5,
            fuelSaved = 2.0,
            radiationPenalty = 0.0,
            sustainabilityBonus = 0.1
        )
        
        val safetyMetrics = SafetyMetrics(
            maxDeceleration = 2.0,
            minFollowingDistance = 4.0,
            collisionDetected = false,
            suddenBrakingDetected = false,
            speedLimitViolation = false
        )
        
        val result = oracleService.validateManeuver(offer, 32.0, safetyMetrics)
        
        assertTrue(result.isValid())
        assertTrue(result.yieldOccurred)
        assertTrue(result.maneuverWasSafe)
        assertTrue(result.timeSavingPositive)
    }

    @Test
    fun testValidation_unsafeManeuver() {
        val offer = NegotiationOffer(
            offerId = "TEST_002",
            requesterId = "REQ_001",
            responderId = "RESP_001",
            rewardAmount = 10.0,
            estimatedTimeSaved = 30.0,
            congestionLevel = 0.5,
            fuelSaved = 2.0,
            radiationPenalty = 0.0,
            sustainabilityBonus = 0.1
        )
        
        val safetyMetrics = SafetyMetrics(
            maxDeceleration = 5.0,  // Too high!
            minFollowingDistance = 1.0,  // Too close!
            collisionDetected = false,
            suddenBrakingDetected = true,
            speedLimitViolation = false
        )
        
        val result = oracleService.validateManeuver(offer, 32.0, safetyMetrics)
        
        assertFalse(result.isValid())
        assertFalse(result.maneuverWasSafe)
    }

    @Test
    fun testSystemMetrics_calculation() {
        val metrics = SystemMetrics(
            totalRewards = 100.0,
            totalWaitingCosts = 20.0,
            totalPenalties = 5.0,
            radiationPenalty = 10.0,
            sustainabilityBonus = 15.0
        )
        
        // V(t) = Σr - Σw - Σp
        val systemReward = metrics.calculateSystemReward()
        assertEquals(75.0, systemReward, 0.01)
        
        // V_net(t) = V(t) - f(A,t) + Sus(t)
        val netValue = metrics.calculateNetSystemValue()
        assertEquals(80.0, netValue, 0.01)
    }

    @Test
    fun testSystemMetrics_successRate() {
        val metrics = SystemMetrics()
        
        metrics.recordNegotiation(10.0, 2.0, 0.0, true)
        metrics.recordNegotiation(15.0, 3.0, 0.0, true)
        metrics.recordNegotiation(8.0, 1.0, 0.0, false)
        
        // 2 successful out of 3 total = 66.67%
        assertEquals(0.667, metrics.getSuccessRate(), 0.01)
        assertEquals(3, metrics.totalTransactions)
    }

    @Test
    fun testPricingParameters_radiationPenalty() {
        val params = PricingParameters()
        
        // No penalty if under threshold
        val noPenalty = params.calculateRadiationPenalty(200.0)
        assertEquals(0.0, noPenalty, 0.01)
        
        // Penalty kicks in after threshold
        val withPenalty = params.calculateRadiationPenalty(400.0)
        assertTrue(withPenalty < 0)  // Should be negative
    }

    @Test
    fun testPricingParameters_adaptiveLearning() {
        val params = PricingParameters()
        val initialBaseReward = params.baseRewardPerSecond
        
        // Low acceptance rate should increase prices
        params.adjustPricingBasedOnAcceptanceRate(0.3)
        assertTrue(params.baseRewardPerSecond > initialBaseReward)
        
        // High acceptance rate should decrease prices
        params.adjustPricingBasedOnAcceptanceRate(0.95)
        assertTrue(params.baseRewardPerSecond < initialBaseReward)
    }

    @Test
    fun testNegotiationOffer_netReward() {
        val offer = NegotiationOffer(
            offerId = "TEST_003",
            requesterId = "REQ_001",
            responderId = "RESP_001",
            rewardAmount = 10.0,
            estimatedTimeSaved = 30.0,
            congestionLevel = 0.5,
            fuelSaved = 2.0,
            radiationPenalty = -2.0,
            sustainabilityBonus = 1.5
        )
        
        // Net = reward - penalty + bonus = 10 - (-2) + 1.5 = 13.5
        assertEquals(13.5, offer.getNetReward(), 0.01)
    }

    @Test
    fun testNegotiationOffer_expiration() {
        val offer = NegotiationOffer(
            offerId = "TEST_004",
            requesterId = "REQ_001",
            responderId = "RESP_001",
            rewardAmount = 10.0,
            estimatedTimeSaved = 30.0,
            congestionLevel = 0.5,
            fuelSaved = 2.0,
            radiationPenalty = 0.0,
            sustainabilityBonus = 0.0,
            expiresAt = java.util.Date(System.currentTimeMillis() - 1000)  // Already expired
        )
        
        assertTrue(offer.isExpired())
    }

    @Test
    fun testDriver_actions() {
        // Test that all driver actions are defined
        val actions = Driver.Action.values()
        assertEquals(3, actions.size)
        assertTrue(actions.contains(Driver.Action.YIELD))
        assertTrue(actions.contains(Driver.Action.WAIT))
        assertTrue(actions.contains(Driver.Action.NOT_YIELD))
    }

    @Test
    fun testSafetyMetrics_isSafe() {
        val safe = SafetyMetrics(
            maxDeceleration = 2.0,
            minFollowingDistance = 3.0,
            collisionDetected = false,
            suddenBrakingDetected = false,
            speedLimitViolation = false
        )
        assertTrue(safe.isSafe())
        
        val unsafe = SafetyMetrics(
            maxDeceleration = 5.0,
            minFollowingDistance = 1.0,
            collisionDetected = true,
            suddenBrakingDetected = true,
            speedLimitViolation = true
        )
        assertFalse(unsafe.isSafe())
    }
}
