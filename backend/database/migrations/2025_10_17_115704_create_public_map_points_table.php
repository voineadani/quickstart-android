<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('public_map_points', function (Blueprint $table) {
            $table->id();
            $table->foreignId('protocol_id')->constrained('protocols')->onDelete('cascade');
            $table->json('disease_flags');
            $table->json('public_fields');
            $table->timestamps();
            
            $table->index('protocol_id');
        });
        
        // Add spatial column using raw SQL for POINT geometry
        DB::statement('ALTER TABLE public_map_points ADD geom POINT NOT NULL SRID 4326');
        DB::statement('CREATE SPATIAL INDEX geom_idx ON public_map_points(geom)');
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('public_map_points');
    }
};
