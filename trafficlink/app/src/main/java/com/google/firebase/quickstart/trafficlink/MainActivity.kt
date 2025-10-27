package com.google.firebase.quickstart.trafficlink

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.firebase.quickstart.trafficlink.models.Driver
import com.google.firebase.quickstart.trafficlink.services.TrafficLinkService

/**
 * Main activity for TrafficLink application.
 * Displays dashboard, system metrics, and active offers.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var trafficLinkService: TrafficLinkService
    private lateinit var currentDriver: Driver
    
    private lateinit var balanceText: TextView
    private lateinit var reputationText: TextView
    private lateinit var rateText: TextView
    private lateinit var systemRewardText: TextView
    private lateinit var netSystemValueText: TextView
    private lateinit var successRateText: TextView
    private lateinit var totalTransactionsText: TextView
    private lateinit var offersRecyclerView: RecyclerView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Initialize service and current driver
        trafficLinkService = TrafficLinkService()
        currentDriver = Driver(
            id = "DRIVER_001",
            name = "Test Driver",
            isParticipant = true,
            tlkBalance = 100.0,
            reputation = 1.0
        )

        // Initialize views
        balanceText = findViewById(R.id.balance_text)
        reputationText = findViewById(R.id.reputation_text)
        rateText = findViewById(R.id.rate_text)
        systemRewardText = findViewById(R.id.system_reward_text)
        netSystemValueText = findViewById(R.id.net_system_value_text)
        successRateText = findViewById(R.id.success_rate_text)
        totalTransactionsText = findViewById(R.id.total_transactions_text)
        offersRecyclerView = findViewById(R.id.offers_recycler_view)

        // Setup RecyclerView
        offersRecyclerView.layoutManager = LinearLayoutManager(this)

        // Setup buttons
        findViewById<Button>(R.id.create_offer_button).setOnClickListener {
            createTestOffer()
        }

        findViewById<Button>(R.id.view_offers_button).setOnClickListener {
            refreshOffers()
        }

        // Initial UI update
        updateUI()
    }

    override fun onResume() {
        super.onResume()
        updateUI()
        trafficLinkService.cleanupExpiredOffers()
    }

    /**
     * Update all UI elements with current state.
     */
    private fun updateUI() {
        // Update driver info
        balanceText.text = getString(R.string.balance_label) + " ${String.format("%.2f", currentDriver.tlkBalance)} TLK"
        reputationText.text = getString(R.string.reputation_label) + " ${String.format("%.2f", currentDriver.reputation)}"
        
        // Update token economics
        val tokenEcon = trafficLinkService.getTokenEconomics()
        rateText.text = getString(R.string.tlk_usdt_rate) + " ${String.format("%.4f", tokenEcon.getTlkToUsdtRate())}"
        
        // Update system metrics
        val metrics = trafficLinkService.getSystemMetrics()
        systemRewardText.text = getString(R.string.system_reward_label) + " ${String.format("%.2f", metrics.calculateSystemReward())}"
        netSystemValueText.text = getString(R.string.net_system_value_label) + " ${String.format("%.2f", metrics.calculateNetSystemValue())}"
        successRateText.text = getString(R.string.success_rate_label) + " ${String.format("%.1f%%", metrics.getSuccessRate() * 100)}"
        totalTransactionsText.text = getString(R.string.total_transactions_label) + " ${metrics.totalTransactions}"
        
        // Update offers list
        refreshOffers()
    }

    /**
     * Create a test offer for demonstration.
     */
    private fun createTestOffer() {
        // Create a test responder
        val responder = Driver(
            id = "DRIVER_002",
            name = "Responder",
            isParticipant = true,
            tlkBalance = 50.0,
            reputation = 1.2
        )

        // Create offer with test parameters
        val offer = trafficLinkService.createOffer(
            requester = currentDriver,
            responder = responder,
            timeSaved = 30.0,  // 30 seconds
            congestionLevel = 0.6,  // 60% congestion
            fuelSaved = 2.0,  // 2 units fuel
            numAvailableYielders = 5,
            timeInArea = 60.0  // 60 seconds in area
        )

        if (offer != null) {
            Toast.makeText(this, getString(R.string.offer_created), Toast.LENGTH_SHORT).show()
            
            // Show offer details
            val message = """
                Offer Created!
                ID: ${offer.offerId.substring(0, 8)}...
                Reward: ${String.format("%.2f", offer.rewardAmount)} TLK
                Net Reward: ${String.format("%.2f", offer.getNetReward())} TLK
                Time Saved: ${String.format("%.1f", offer.estimatedTimeSaved)}s
                Expires: ${android.text.format.DateFormat.format("HH:mm:ss", offer.expiresAt)}
            """.trimIndent()
            
            android.app.AlertDialog.Builder(this)
                .setTitle("New Offer")
                .setMessage(message)
                .setPositiveButton("OK") { dialog, _ -> dialog.dismiss() }
                .show()
            
            updateUI()
        } else {
            Toast.makeText(this, getString(R.string.insufficient_balance), Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * Refresh the list of active offers.
     */
    private fun refreshOffers() {
        val offers = trafficLinkService.getActiveOffers()
        // In a real app, we'd use a proper RecyclerView adapter
        // For now, just show count
        Toast.makeText(this, "Active Offers: ${offers.size}", Toast.LENGTH_SHORT).show()
    }

    companion object {
        private const val TAG = "MainActivity"
    }
}
