<?php

namespace App\Http\Controllers;

use App\Models\Protocol;
use App\Models\Result;
use Illuminate\Http\Request;

class ResultController extends Controller
{
    public function store(Request $request, Protocol $protocol)
    {
        $validated = $request->validate([
            'trichinella_result' => 'nullable|in:positive,negative,pending',
            'asf_result' => 'nullable|in:positive,negative,pending',
        ]);

        $result = Result::updateOrCreate(
            ['protocol_id' => $protocol->id],
            [
                'trichinella_result' => $validated['trichinella_result'] ?? 'pending',
                'trichinella_recorded_at' => isset($validated['trichinella_result']) ? now() : null,
                'asf_result' => $validated['asf_result'] ?? 'pending',
                'asf_recorded_at' => isset($validated['asf_result']) ? now() : null,
                'recorded_by' => $request->user()->id,
            ]
        );

        return response()->json([
            'data' => $result->load(['protocol', 'recordedByUser']),
            'message' => 'Result recorded successfully',
        ], 201);
    }

    public function show(Protocol $protocol)
    {
        $result = $protocol->result;

        if (!$result) {
            return response()->json([
                'data' => null,
                'message' => 'No results available yet',
            ]);
        }

        return response()->json([
            'data' => $result->load(['recordedByUser']),
        ]);
    }
}
