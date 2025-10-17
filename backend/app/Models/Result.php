<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Spatie\Activitylog\Traits\LogsActivity;
use Spatie\Activitylog\LogOptions;

class Result extends Model
{
    use LogsActivity;

    protected $fillable = [
        'protocol_id',
        'trichinella_result',
        'trichinella_recorded_at',
        'asf_result',
        'asf_recorded_at',
        'recorded_by',
    ];

    protected $casts = [
        'trichinella_recorded_at' => 'datetime',
        'asf_recorded_at' => 'datetime',
    ];

    public function protocol(): BelongsTo
    {
        return $this->belongsTo(Protocol::class);
    }

    public function recordedByUser(): BelongsTo
    {
        return $this->belongsTo(User::class, 'recorded_by');
    }

    public function getActivitylogOptions(): LogOptions
    {
        return LogOptions::defaults()
            ->logOnly(['trichinella_result', 'trichinella_recorded_at', 'asf_result', 'asf_recorded_at', 'recorded_by'])
            ->logOnlyDirty();
    }
}
