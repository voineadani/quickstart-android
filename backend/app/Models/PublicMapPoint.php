<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class PublicMapPoint extends Model
{
    protected $fillable = [
        'protocol_id',
        'disease_flags',
        'public_fields',
    ];

    protected $casts = [
        'disease_flags' => 'array',
        'public_fields' => 'array',
    ];

    public function protocol(): BelongsTo
    {
        return $this->belongsTo(Protocol::class);
    }
}
