<?php

namespace App\Http\Controllers;

use App\Models\Lab;
use Illuminate\Http\Request;

class LabController extends Controller
{
    public function index()
    {
        $labs = Lab::paginate(15);
        
        return response()->json([
            'data' => $labs,
        ]);
    }

    public function store(Request $request)
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'admin_address' => 'nullable|string',
            'contact_info' => 'nullable|string',
            'email' => 'nullable|email|max:255',
            'authorized_for_trichinella' => 'boolean',
            'authorized_for_asf' => 'boolean',
        ]);

        $lab = Lab::create($validated);

        return response()->json([
            'data' => $lab,
            'message' => 'Lab created successfully',
        ], 201);
    }

    public function show(Lab $lab)
    {
        return response()->json([
            'data' => $lab->load(['users', 'protocols']),
        ]);
    }

    public function update(Request $request, Lab $lab)
    {
        $validated = $request->validate([
            'name' => 'sometimes|required|string|max:255',
            'admin_address' => 'nullable|string',
            'contact_info' => 'nullable|string',
            'email' => 'nullable|email|max:255',
            'authorized_for_trichinella' => 'boolean',
            'authorized_for_asf' => 'boolean',
        ]);

        $lab->update($validated);

        return response()->json([
            'data' => $lab,
            'message' => 'Lab updated successfully',
        ]);
    }

    public function destroy(Lab $lab)
    {
        $lab->delete();

        return response()->json([
            'message' => 'Lab deleted successfully',
        ]);
    }
}
