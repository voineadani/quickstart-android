<?php

use App\Models\User;
use App\Models\Role;

test('user can login with valid credentials', function () {
    $role = Role::create(['name' => 'HUNTER', 'description' => 'Hunter']);
    $user = User::factory()->create([
        'email' => 'test@example.com',
        'password' => bcrypt('password'),
        'role_id' => $role->id,
    ]);

    $response = $this->postJson('/api/auth/login', [
        'email' => 'test@example.com',
        'password' => 'password',
    ]);

    $response->assertStatus(200)
             ->assertJsonStructure(['data' => ['user', 'token']]);
});

test('user cannot login with invalid credentials', function () {
    $response = $this->postJson('/api/auth/login', [
        'email' => 'wrong@example.com',
        'password' => 'wrongpassword',
    ]);

    $response->assertStatus(422);
});

test('authenticated user can access protected routes', function () {
    $role = Role::create(['name' => 'HUNTER', 'description' => 'Hunter']);
    $user = User::factory()->create(['role_id' => $role->id]);
    
    $response = $this->actingAs($user, 'sanctum')->getJson('/api/me');

    $response->assertStatus(200)
             ->assertJson(['data' => ['id' => $user->id]]);
});
