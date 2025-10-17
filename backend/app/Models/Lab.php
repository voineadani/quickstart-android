<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Spatie\Activitylog\Traits\LogsActivity;
use Spatie\Activitylog\LogOptions;

class Lab extends Model
{
    use LogsActivity;

    protected $fillable = [
        'name',
        'admin_address',
        'contact_info',
        'email',
        'authorized_for_trichinella',
        'authorized_for_asf',
    ];

    protected $casts = [
        'authorized_for_trichinella' => 'boolean',
        'authorized_for_asf' => 'boolean',
    ];

    public function users(): HasMany
    {
        return $this->hasMany(User::class);
    }

    public function protocols(): HasMany
    {
        return $this->hasMany(Protocol::class);
    }

    public function getActivitylogOptions(): LogOptions
    {
        return LogOptions::defaults()
            ->logOnly(['name', 'admin_address', 'contact_info', 'email', 'authorized_for_trichinella', 'authorized_for_asf'])
            ->logOnlyDirty();
    }
}
