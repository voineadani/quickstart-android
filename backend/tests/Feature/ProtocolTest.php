<?php

use App\Models\User;
use App\Models\Role;
use App\Models\Protocol;

test('hunter can create protocol', function () {
    $role = Role::create(['name' => 'HUNTER', 'description' => 'Hunter']);
    $user = User::factory()->create(['role_id' => $role->id]);

    $response = $this->actingAs($user, 'sanctum')->postJson('/api/protocols', [
        'game_species' => 'Deer',
        'sample_type' => 'tissue',
        'sample_barcode' => 'TEST-001',
        'gps_lat' => 45.5,
        'gps_lon' => -75.5,
    ]);

    $response->assertStatus(201);
    $this->assertDatabaseHas('protocols', ['sample_barcode' => 'TEST-001']);
});

test('hunter can only see their own protocols', function () {
    $role = Role::create(['name' => 'HUNTER', 'description' => 'Hunter']);
    $user1 = User::factory()->create(['role_id' => $role->id]);
    $user2 = User::factory()->create(['role_id' => $role->id]);
    
    $protocol = Protocol::factory()->create(['user_id' => $user2->id]);

    $response = $this->actingAs($user1, 'sanctum')->getJson('/api/protocols');

    $response->assertStatus(200)
             ->assertJsonMissing(['id' => $protocol->id]);
});
