<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('protocols', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained('users')->onDelete('cascade');
            $table->string('game_species');
            $table->string('animal_sex')->nullable();
            $table->string('animal_age')->nullable();
            $table->decimal('animal_weight', 8, 2)->nullable();
            $table->string('sample_type');
            $table->string('sample_barcode')->unique();
            $table->string('category')->nullable();
            $table->string('phone_from')->nullable();
            $table->foreignId('lab_id')->nullable()->constrained('labs')->onDelete('set null');
            $table->timestamp('requested_from_lab_at')->nullable();
            $table->timestamp('submitted_at')->nullable();
            $table->timestamp('created_in_system_at')->useCurrent();
            $table->timestamps();
            
            $table->index('sample_barcode');
            $table->index('lab_id');
            $table->index('created_in_system_at');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('protocols');
    }
};
