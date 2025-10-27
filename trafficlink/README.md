# TrafficLink: Decentralized Traffic Coordination System

TrafficLink is a decentralized, incentive-based traffic coordination system that allows drivers to request right-of-way (e.g., merging, overtaking) and compensate other drivers who yield, using tokenized rewards under strict safety and legality constraints.

## Mission

Reduce congestion and travel friction by enabling efficient traffic negotiation—never rewarding unsafe or chaotic behavior.

## Core Components

### 1. Economic Model / Tokenomics

- **Token Symbol**: TLK (ERC-20 compatible)
- **Purpose**: Compensation medium for yielding right-of-way
- **Exchange**: TLK ↔ USDT via constant-product AMM (x·y=k)
- **Implementation**: `TokenEconomics.kt`

### 2. Dynamic Pricing Algorithm

Reward `r(t)` is calculated based on:
- ΔT: Estimated time saved
- Local congestion level
- Fuel/energy saved
- Responder reputation
- Scarcity of available yielders
- Radiation penalty (discourages loitering)
- Sustainability bonus (rewards eco-behavior)

**Adaptive Learning**: The system uses reinforcement learning to adjust pricing:
- If offers are rejected often → increase rewards
- If accepted instantly → decrease rewards

**Implementation**: `TrafficLinkService.kt`, `PricingParameters.kt`

### 3. Negotiation Protocol

#### Lifecycle Phases:

1. **Initiation (Request)**
   - Driver A proposes offer with reward `r(t)` in TLK
   - Tokens are escrowed from Driver A

2. **Agreement**
   - Driver B accepts within time limit (default: 30 seconds)
   - Legal and physical feasibility is checked

3. **Validation (Off-chain)**
   - Verify that yield actually occurred
   - Ensure maneuver was safe (no sudden braking/collision)
   - Confirm Driver A gained positive ΔT
   - Handled by `TrafficOracleService`

4. **Settlement**
   - If valid: payout tokens to Driver B
   - If invalid: refund or dispute
   - Update driver reputations

**Implementation**: `NegotiationOffer.kt`, `TrafficLinkService.kt`

### 4. Validation System

The `TrafficOracleService` provides off-chain validation using:
- GPS/location data
- Vehicle telemetry
- Safety metrics (deceleration, following distance)
- Cryptographic attestation signatures

**Implementation**: `TrafficOracleService.kt`, `SafetyMetrics`

### 5. System Metrics

Tracks overall system performance:

- **V(t)**: Total system reward = Σ[r_i(t) - w_i(t) - p_i(t)]
- **V_net(t)**: Net system value = V(t) - f(A,t) + Sus(t)
- Success rate, total transactions, etc.

**Implementation**: `SystemMetrics.kt`

## Key Features

### Tunable Parameters

All system parameters are configurable in `PricingParameters.kt`:

```kotlin
- baseRewardPerSecond: Base TLK per second saved
- congestionMultiplier: Multiplier for high congestion
- fuelSavingsFactor: TLK per unit fuel saved
- reputationWeight: Impact of reputation
- scarcityMultiplier: Increases when yielders are scarce
- radiationPenaltyRate: Penalty for loitering
- sustainabilityBonusRate: Bonus for eco-behavior
- learningRate: Adaptive pricing adjustment rate
- minReward / maxReward: Reward bounds
- safetyBuffer: Extra time for safety
```

### Safety Constraints

The system enforces strict safety rules:
- Maximum deceleration < 3.5 m/s²
- Minimum following distance ≥ 2.0 meters
- No collision detection
- No sudden braking
- No speed limit violations

Failed validations result in:
- Token refund to requester
- Reputation penalty for responder
- Dispute status for investigation

## Usage

### Creating an Offer

```kotlin
val service = TrafficLinkService()

val offer = service.createOffer(
    requester = requesterDriver,
    responder = responderDriver,
    timeSaved = 30.0,           // seconds
    congestionLevel = 0.6,       // 0-1 scale
    fuelSaved = 2.0,            // units
    numAvailableYielders = 5,
    timeInArea = 60.0           // seconds
)
```

### Accepting an Offer

```kotlin
val accepted = service.acceptOffer(offer.offerId, responderDriver)
```

### Validating and Settling

```kotlin
val safetyMetrics = SafetyMetrics(
    maxDeceleration = 2.5,
    minFollowingDistance = 3.0,
    collisionDetected = false,
    suddenBrakingDetected = false,
    speedLimitViolation = false
)

val result = service.validateAndSettle(
    offerId = offer.offerId,
    actualTimeSaved = 32.0,
    safetyMetrics = safetyMetrics,
    requester = requesterDriver,
    responder = responderDriver
)
```

## Testing

Comprehensive test suite in `TrafficLinkInstrumentedTest.kt` covers:

- Token economics (constant-product AMM)
- Dynamic pricing algorithms
- Complete negotiation lifecycle
- Validation logic
- System metrics calculations
- Safety constraints
- Adaptive learning

Run tests:
```bash
./gradlew :trafficlink:app:connectedAndroidTest
```

## Architecture

```
models/
├── Driver.kt              - Driver entity with balance, reputation
├── TokenEconomics.kt      - TLK token and AMM implementation
├── NegotiationOffer.kt    - Offer lifecycle and validation result
├── SystemMetrics.kt       - System-wide performance metrics
└── PricingParameters.kt   - Tunable parameters

services/
├── TrafficLinkService.kt    - Main service: negotiation + pricing
└── TrafficOracleService.kt  - Off-chain validation service
```

## Mathematical Formulations

### System Reward
```
V(t) = Σ[r_i(t) - w_i(t) - p_i(t)]
```

Where:
- `r_i(t)`: Reward for yielding (TLK)
- `w_i(t)`: Waiting cost (time/inconvenience)
- `p_i(t)`: Penalty for refusal

### Net System Value
```
V_net(t) = V(t) - f(A,t) + Sus(t)
```

Where:
- `f(A,t)`: Radiation penalty (negative)
- `Sus(t)`: Sustainability bonus (positive)

### Constant-Product AMM
```
x · y = k
```

Where:
- `x`: TLK reserve
- `y`: USDT reserve
- `k`: Constant product

## Firebase Integration

The module integrates with Firebase services:
- Firebase Auth: Driver authentication
- Firebase Firestore: Distributed offer storage
- Firebase Database: Real-time negotiation updates

## Future Enhancements

1. **Smart Contract Integration**: Deploy actual ERC-20 contracts on Ethereum/Polygon
2. **Real Sensor Integration**: Connect to vehicle OBD-II, GPS, cameras
3. **Machine Learning**: Advanced demand prediction and pricing optimization
4. **Multi-hop Negotiations**: Complex traffic scenarios with multiple participants
5. **Regulatory Compliance**: Integration with traffic management systems

## License

See repository root LICENSE file.

## Contributing

See repository root CONTRIBUTING.md file.
