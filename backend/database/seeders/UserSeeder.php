<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class UserSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $adminRole = \App\Models\Role::where('name', 'ADMIN')->first();
        $hunterRole = \App\Models\Role::where('name', 'HUNTER')->first();
        $labRole = \App\Models\Role::where('name', 'LAB')->first();
        $centralLab = \App\Models\Lab::where('name', 'Central Testing Laboratory')->first();

        // Create admin user
        \App\Models\User::create([
            'first_name' => 'Admin',
            'last_name' => 'User',
            'username' => 'admin',
            'phone' => '+1-555-1000',
            'name' => 'Admin User',
            'email' => 'admin@hunting-data.example.com',
            'password' => bcrypt('password'),
            'role_id' => $adminRole->id,
            'status' => 'active',
        ]);

        // Create hunter user
        \App\Models\User::create([
            'first_name' => 'John',
            'last_name' => 'Hunter',
            'username' => 'jhunter',
            'phone' => '+1-555-2000',
            'name' => 'John Hunter',
            'email' => 'john.hunter@example.com',
            'password' => bcrypt('password'),
            'role_id' => $hunterRole->id,
            'status' => 'active',
        ]);

        // Create lab user
        \App\Models\User::create([
            'first_name' => 'Lab',
            'last_name' => 'Technician',
            'username' => 'labtech',
            'phone' => '+1-555-3000',
            'name' => 'Lab Technician',
            'email' => 'lab.tech@central-lab.example.com',
            'password' => bcrypt('password'),
            'role_id' => $labRole->id,
            'lab_id' => $centralLab->id,
            'status' => 'active',
        ]);
    }
}
