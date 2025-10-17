<?php

namespace App\Http\Controllers;

use App\Models\Protocol;
use App\Models\LocationData;
use Illuminate\Http\Request;

class ProtocolController extends Controller
{
    public function index(Request $request)
    {
        $user = $request->user();
        
        $query = Protocol::with(['user', 'lab', 'locationData', 'result']);

        // Hunters see only their own protocols
        if ($user->role->name === 'HUNTER') {
            $query->where('user_id', $user->id);
        }
        
        // Lab users see protocols assigned to their lab
        if ($user->role->name === 'LAB') {
            $query->where('lab_id', $user->lab_id);
        }

        $protocols = $query->paginate(15);

        return response()->json([
            'data' => $protocols,
        ]);
    }

    public function store(Request $request)
    {
        $validated = $request->validate([
            'game_species' => 'required|string|max:255',
            'animal_sex' => 'nullable|string|max:50',
            'animal_age' => 'nullable|string|max:50',
            'animal_weight' => 'nullable|numeric',
            'sample_type' => 'required|string|max:255',
            'sample_barcode' => 'required|string|max:255|unique:protocols',
            'category' => 'nullable|string|max:255',
            'phone_from' => 'nullable|string|max:20',
            'gps_lat' => 'required|numeric|between:-90,90',
            'gps_lon' => 'required|numeric|between:-180,180',
            'admin_address' => 'nullable|string',
        ]);

        $protocol = Protocol::create([
            'user_id' => $request->user()->id,
            'game_species' => $validated['game_species'],
            'animal_sex' => $validated['animal_sex'] ?? null,
            'animal_age' => $validated['animal_age'] ?? null,
            'animal_weight' => $validated['animal_weight'] ?? null,
            'sample_type' => $validated['sample_type'],
            'sample_barcode' => $validated['sample_barcode'],
            'category' => $validated['category'] ?? null,
            'phone_from' => $validated['phone_from'] ?? null,
            'created_in_system_at' => now(),
        ]);

        LocationData::create([
            'protocol_id' => $protocol->id,
            'gps_lat' => $validated['gps_lat'],
            'gps_lon' => $validated['gps_lon'],
            'admin_address' => $validated['admin_address'] ?? null,
        ]);

        return response()->json([
            'data' => $protocol->load(['locationData']),
            'message' => 'Protocol created successfully',
        ], 201);
    }

    public function show(Protocol $protocol)
    {
        $user = request()->user();

        // Check authorization
        if ($user->role->name === 'HUNTER' && $protocol->user_id !== $user->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        if ($user->role->name === 'LAB' && $protocol->lab_id !== $user->lab_id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        return response()->json([
            'data' => $protocol->load(['user', 'lab', 'locationData', 'result']),
        ]);
    }

    public function assignLab(Request $request, Protocol $protocol)
    {
        $validated = $request->validate([
            'lab_id' => 'required|exists:labs,id',
        ]);

        $protocol->update([
            'lab_id' => $validated['lab_id'],
            'requested_from_lab_at' => now(),
        ]);

        return response()->json([
            'data' => $protocol->load(['lab']),
            'message' => 'Lab assigned successfully',
        ]);
    }
}
