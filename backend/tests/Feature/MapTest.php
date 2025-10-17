<?php

test('public map endpoint returns geojson', function () {
    $response = $this->getJson('/api/public/map/points');

    $response->assertStatus(200)
             ->assertJsonStructure(['type', 'features']);
});
