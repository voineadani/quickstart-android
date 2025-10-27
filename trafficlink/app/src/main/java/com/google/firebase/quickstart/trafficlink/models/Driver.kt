package com.google.firebase.quickstart.trafficlink.models

/**
 * Represents a driver in the TrafficLink system.
 */
data class Driver(
    val id: String,
    val name: String,
    val isParticipant: Boolean = true,  // CT (participant) vs CWT (non-participant)
    var tlkBalance: Double = 100.0,  // TLK token balance
    var reputation: Double = 1.0,  // Reputation score (affects pricing)
    var location: Location = Location()
) {
    enum class Action {
        YIELD,       // Agree to yield right-of-way
        WAIT,        // Wait for other driver
        NOT_YIELD    // Refuse to yield
    }
}

/**
 * Represents a location in the system.
 */
data class Location(
    val latitude: Double = 0.0,
    val longitude: Double = 0.0,
    val area: String = "A"  // Area identifier
)
