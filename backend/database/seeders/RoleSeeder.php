<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class RoleSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $roles = [
            ['name' => 'HUNTER', 'description' => 'Hunter role - can create protocols and view own results'],
            ['name' => 'LAB', 'description' => 'Lab role - can view assigned protocols and enter test results'],
            ['name' => 'ADMIN', 'description' => 'Admin role - full access to all resources'],
        ];

        foreach ($roles as $role) {
            \App\Models\Role::create($role);
        }
    }
}
