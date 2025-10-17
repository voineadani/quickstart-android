<?php

use App\Http\Controllers\AuthController;
use App\Http\Controllers\LabController;
use App\Http\Controllers\MapController;
use App\Http\Controllers\ProtocolController;
use App\Http\Controllers\ResultController;
use App\Http\Controllers\UserController;
use Illuminate\Support\Facades\Route;

// Public routes
Route::post('/auth/register', [AuthController::class, 'register']);
Route::post('/auth/login', [AuthController::class, 'login']);

// Public map endpoint
Route::get('/public/map/points', [MapController::class, 'points']);

// Protected routes
Route::middleware('auth:sanctum')->group(function () {
    // Auth
    Route::post('/auth/logout', [AuthController::class, 'logout']);
    Route::get('/me', [AuthController::class, 'me']);

    // Protocols
    Route::get('/protocols', [ProtocolController::class, 'index']);
    Route::post('/protocols', [ProtocolController::class, 'store']);
    Route::get('/protocols/{protocol}', [ProtocolController::class, 'show']);
    Route::post('/protocols/{protocol}/assign-lab', [ProtocolController::class, 'assignLab'])
        ->middleware('role:admin');

    // Results
    Route::post('/protocols/{protocol}/results', [ResultController::class, 'store'])
        ->middleware('role:lab|admin');
    Route::get('/protocols/{protocol}/results', [ResultController::class, 'show']);

    // Labs (Admin only)
    Route::middleware('role:admin')->group(function () {
        Route::get('/labs', [LabController::class, 'index']);
        Route::post('/labs', [LabController::class, 'store']);
        Route::get('/labs/{lab}', [LabController::class, 'show']);
        Route::patch('/labs/{lab}', [LabController::class, 'update']);
        Route::delete('/labs/{lab}', [LabController::class, 'destroy']);
    });

    // Users (Admin only)
    Route::middleware('role:admin')->group(function () {
        Route::get('/users', [UserController::class, 'index']);
        Route::post('/users', [UserController::class, 'store']);
        Route::get('/users/{user}', [UserController::class, 'show']);
        Route::patch('/users/{user}', [UserController::class, 'update']);
        Route::delete('/users/{user}', [UserController::class, 'destroy']);
    });
});
