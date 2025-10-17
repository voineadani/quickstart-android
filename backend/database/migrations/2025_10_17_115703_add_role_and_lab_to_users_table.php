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
        Schema::table('users', function (Blueprint $table) {
            $table->string('first_name')->after('id');
            $table->string('last_name')->after('first_name');
            $table->string('username')->unique()->after('last_name');
            $table->string('phone')->nullable()->after('username');
            $table->foreignId('role_id')->nullable()->after('password')->constrained('roles')->onDelete('set null');
            $table->foreignId('lab_id')->nullable()->after('role_id')->constrained('labs')->onDelete('set null');
            $table->enum('status', ['active', 'inactive'])->default('active')->after('lab_id');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->dropForeign(['role_id']);
            $table->dropForeign(['lab_id']);
            $table->dropColumn(['first_name', 'last_name', 'username', 'phone', 'role_id', 'lab_id', 'status']);
        });
    }
};
