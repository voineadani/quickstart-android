<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasOne;
use Spatie\Activitylog\Traits\LogsActivity;
use Spatie\Activitylog\LogOptions;

class Protocol extends Model
{
    use LogsActivity;

    protected $fillable = [
        'user_id',
        'game_species',
        'animal_sex',
        'animal_age',
        'animal_weight',
        'sample_type',
        'sample_barcode',
        'category',
        'phone_from',
        'lab_id',
        'requested_from_lab_at',
        'submitted_at',
        'created_in_system_at',
    ];

    protected $casts = [
        'animal_weight' => 'decimal:2',
        'requested_from_lab_at' => 'datetime',
        'submitted_at' => 'datetime',
        'created_in_system_at' => 'datetime',
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function lab(): BelongsTo
    {
        return $this->belongsTo(Lab::class);
    }

    public function locationData(): HasOne
    {
        return $this->hasOne(LocationData::class);
    }

    public function result(): HasOne
    {
        return $this->hasOne(Result::class);
    }

    public function publicMapPoint(): HasOne
    {
        return $this->hasOne(PublicMapPoint::class);
    }

    public function getActivitylogOptions(): LogOptions
    {
        return LogOptions::defaults()
            ->logOnly(['game_species', 'sample_barcode', 'lab_id', 'requested_from_lab_at', 'submitted_at'])
            ->logOnlyDirty();
    }
}
