<?php

namespace App\Http\Controllers;

use App\Models\Result;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;

class MapController extends Controller
{
    public function points(Request $request)
    {
        $request->validate([
            'bbox' => 'nullable|string', // Format: min_lon,min_lat,max_lon,max_lat
            'disease' => 'nullable|string', // trichinella, asf
        ]);

        $cacheKey = 'map_points_' . md5($request->fullUrl());

        $geoJson = Cache::remember($cacheKey, 900, function () use ($request) {
            // Get only positive results with location data
            $query = Result::with(['protocol.locationData'])
                ->where(function ($q) {
                    $q->where('trichinella_result', 'positive')
                      ->orWhere('asf_result', 'positive');
                });

            // Filter by disease if specified
            if ($request->disease) {
                $diseases = explode(',', $request->disease);
                $query->where(function ($q) use ($diseases) {
                    foreach ($diseases as $disease) {
                        if ($disease === 'trichinella') {
                            $q->orWhere('trichinella_result', 'positive');
                        }
                        if ($disease === 'asf') {
                            $q->orWhere('asf_result', 'positive');
                        }
                    }
                });
            }

            $results = $query->get();

            $features = [];
            foreach ($results as $result) {
                if ($result->protocol && $result->protocol->locationData) {
                    $location = $result->protocol->locationData;
                    
                    // Apply bbox filter if provided
                    if ($request->bbox) {
                        list($minLon, $minLat, $maxLon, $maxLat) = explode(',', $request->bbox);
                        if ($location->gps_lon < $minLon || $location->gps_lon > $maxLon ||
                            $location->gps_lat < $minLat || $location->gps_lat > $maxLat) {
                            continue;
                        }
                    }

                    $diseaseFlags = [];
                    if ($result->trichinella_result === 'positive') {
                        $diseaseFlags[] = 'trichinella';
                    }
                    if ($result->asf_result === 'positive') {
                        $diseaseFlags[] = 'asf';
                    }

                    $features[] = [
                        'type' => 'Feature',
                        'geometry' => [
                            'type' => 'Point',
                            'coordinates' => [
                                (float) $location->gps_lon,
                                (float) $location->gps_lat,
                            ],
                        ],
                        'properties' => [
                            'disease_flags' => $diseaseFlags,
                            'recorded_at' => $result->updated_at->toIso8601String(),
                        ],
                    ];
                }
            }

            return [
                'type' => 'FeatureCollection',
                'features' => $features,
            ];
        });

        return response()->json($geoJson);
    }
}
