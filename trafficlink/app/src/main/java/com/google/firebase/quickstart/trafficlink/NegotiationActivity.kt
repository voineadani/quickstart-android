package com.google.firebase.quickstart.trafficlink

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.firebase.quickstart.trafficlink.models.NegotiationOffer
import com.google.firebase.quickstart.trafficlink.services.SafetyMetrics
import com.google.firebase.quickstart.trafficlink.services.TrafficLinkService

/**
 * Activity for managing individual negotiation offers.
 * Allows accepting, rejecting, and validating offers.
 */
class NegotiationActivity : AppCompatActivity() {

    private lateinit var trafficLinkService: TrafficLinkService
    private lateinit var offer: NegotiationOffer

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_negotiation)

        trafficLinkService = TrafficLinkService()

        // Get offer details from intent
        val offerId = intent.getStringExtra("OFFER_ID") ?: return
        
        // In a real app, we'd load the offer from the service
        // For now, this is a placeholder
        
        setupUI()
    }

    private fun setupUI() {
        findViewById<Button>(R.id.accept_offer_button)?.setOnClickListener {
            // Accept offer logic
            Toast.makeText(this, getString(R.string.offer_accepted), Toast.LENGTH_SHORT).show()
            finish()
        }

        findViewById<Button>(R.id.reject_offer_button)?.setOnClickListener {
            // Reject offer logic
            Toast.makeText(this, getString(R.string.offer_rejected), Toast.LENGTH_SHORT).show()
            finish()
        }

        findViewById<Button>(R.id.validate_offer_button)?.setOnClickListener {
            // Simulate validation with test data
            simulateValidation()
        }
    }

    private fun simulateValidation() {
        // Create test safety metrics
        val safetyMetrics = SafetyMetrics(
            maxDeceleration = 2.5,
            minFollowingDistance = 3.0,
            collisionDetected = false,
            suddenBrakingDetected = false,
            speedLimitViolation = false
        )

        // Show validation result
        val message = if (safetyMetrics.isSafe()) {
            getString(R.string.validation_success)
        } else {
            getString(R.string.validation_failed)
        }

        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        finish()
    }
}
