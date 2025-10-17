<?php

namespace Database\Factories;

use App\Models\User;
use Illuminate\Database\Eloquent\Factories\Factory;

class ProtocolFactory extends Factory
{
    public function definition(): array
    {
        return [
            'user_id' => User::factory(),
            'game_species' => fake()->randomElement(['White-tailed Deer', 'Wild Boar', 'Elk', 'Moose']),
            'animal_sex' => fake()->randomElement(['M', 'F']),
            'animal_age' => fake()->numberBetween(1, 10) . ' years',
            'animal_weight' => fake()->randomFloat(2, 30, 200),
            'sample_type' => fake()->randomElement(['muscle tissue', 'blood', 'organ']),
            'sample_barcode' => fake()->unique()->regexify('[A-Z]{3}-[0-9]{4}'),
            'category' => fake()->randomElement(['Regular Season', 'Special Permit', 'Conservation']),
            'phone_from' => fake()->phoneNumber(),
            'created_in_system_at' => now(),
        ];
    }
}
