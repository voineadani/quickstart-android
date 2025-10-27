package com.google.firebase.quickstart.trafficlink.services

import com.google.firebase.quickstart.trafficlink.models.NegotiationOffer
import com.google.firebase.quickstart.trafficlink.models.ValidationResult
import java.security.MessageDigest
import java.util.Date

/**
 * TrafficOracleService handles off-chain validation of traffic maneuvers.
 * 
 * Validates that:
 * 1. Yield actually occurred
 * 2. Maneuver was safe (no sudden braking/collision)
 * 3. Driver A gained positive ΔT (time saved)
 * 
 * In a real implementation, this would integrate with:
 * - GPS/location services
 * - Vehicle telemetry
 * - Traffic cameras
 * - Other IoT sensors
 */
class TrafficOracleService {
    
    /**
     * Validate a completed negotiation.
     * This is a simplified simulation - real implementation would use actual sensor data.
     */
    fun validateManeuver(
        offer: NegotiationOffer,
        actualTimeSaved: Double,
        safetyMetrics: SafetyMetrics
    ): ValidationResult {
        
        // Check if yield occurred (simplified check)
        val yieldOccurred = actualTimeSaved > 0
        
        // Check if maneuver was safe
        val maneuverWasSafe = safetyMetrics.isSafe()
        
        // Check if time saving was positive and significant
        val timeSavingPositive = actualTimeSaved >= offer.estimatedTimeSaved * 0.5
        
        // Generate attestation signature
        val signature = generateAttestationSignature(
            offer.offerId,
            yieldOccurred,
            maneuverWasSafe,
            timeSavingPositive
        )
        
        val details = buildValidationDetails(
            actualTimeSaved,
            offer.estimatedTimeSaved,
            safetyMetrics
        )
        
        return ValidationResult(
            yieldOccurred = yieldOccurred,
            maneuverWasSafe = maneuverWasSafe,
            timeSavingPositive = timeSavingPositive,
            timestamp = Date(),
            signature = signature,
            details = details
        )
    }
    
    /**
     * Generate a cryptographic signature for attestation.
     * In production, this would use proper cryptographic signing with private keys.
     */
    private fun generateAttestationSignature(
        offerId: String,
        yieldOccurred: Boolean,
        maneuverWasSafe: Boolean,
        timeSavingPositive: Boolean
    ): String {
        val data = "$offerId:$yieldOccurred:$maneuverWasSafe:$timeSavingPositive:${Date().time}"
        val md = MessageDigest.getInstance("SHA-256")
        val hash = md.digest(data.toByteArray())
        return hash.joinToString("") { "%02x".format(it) }
    }
    
    /**
     * Build human-readable validation details.
     */
    private fun buildValidationDetails(
        actualTimeSaved: Double,
        estimatedTimeSaved: Double,
        safetyMetrics: SafetyMetrics
    ): String {
        return """
            Validation Report:
            - Actual time saved: ${"%.2f".format(actualTimeSaved)}s
            - Estimated time saved: ${"%.2f".format(estimatedTimeSaved)}s
            - Max deceleration: ${"%.2f".format(safetyMetrics.maxDeceleration)} m/s²
            - Min following distance: ${"%.2f".format(safetyMetrics.minFollowingDistance)} m
            - Collision detected: ${safetyMetrics.collisionDetected}
        """.trimIndent()
    }
}

/**
 * Safety metrics for validation.
 * In a real system, these would come from vehicle sensors.
 */
data class SafetyMetrics(
    val maxDeceleration: Double = 0.0,      // m/s² - should be < 3.5 for safe
    val minFollowingDistance: Double = 0.0, // meters - should be > 2.0 for safe
    val collisionDetected: Boolean = false,
    val suddenBrakingDetected: Boolean = false,
    val speedLimitViolation: Boolean = false
) {
    fun isSafe(): Boolean {
        return !collisionDetected &&
               !suddenBrakingDetected &&
               !speedLimitViolation &&
               maxDeceleration < 3.5 &&
               minFollowingDistance >= 2.0
    }
}
