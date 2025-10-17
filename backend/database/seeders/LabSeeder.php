<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class LabSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        \App\Models\Lab::create([
            'name' => 'Central Testing Laboratory',
            'admin_address' => '123 Lab Street, Science City, SC 12345',
            'contact_info' => 'Phone: +1-555-0100, Fax: +1-555-0101',
            'email' => 'contact@central-lab.example.com',
            'authorized_for_trichinella' => true,
            'authorized_for_asf' => true,
        ]);

        \App\Models\Lab::create([
            'name' => 'Regional Veterinary Lab',
            'admin_address' => '456 Research Ave, Vetville, VV 54321',
            'contact_info' => 'Phone: +1-555-0200',
            'email' => 'info@regional-vet-lab.example.com',
            'authorized_for_trichinella' => true,
            'authorized_for_asf' => false,
        ]);
    }
}
