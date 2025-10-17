<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class LocationData extends Model
{
    protected $fillable = [
        'protocol_id',
        'gps_lat',
        'gps_lon',
        'admin_address',
    ];

    protected $casts = [
        'gps_lat' => 'decimal:8',
        'gps_lon' => 'decimal:8',
    ];

    public function protocol(): BelongsTo
    {
        return $this->belongsTo(Protocol::class);
    }
}
