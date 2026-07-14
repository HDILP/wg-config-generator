@echo off
chcp 65001 >nul
title WireGuard Win7 补丁安装
echo ═══════════════════════════════════════
echo   WireGuard Windows 7 补丁安装工具
echo ═══════════════════════════════════════
echo.

:: Check KB2921916
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\Packages\Package_for_KB2921916~*" >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] KB2921916 已安装
    set "KB1_DONE=1"
) else (
    echo [✗] KB2921916 未安装
    set "KB1_DONE=0"
)

:: Check KB3033929
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\Packages\Package_for_KB3033929~*" >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] KB3033929 已安装
    set "KB2_DONE=1"
) else (
    echo [✗] KB3033929 未安装
    set "KB2_DONE=0"
)

echo.

if "%KB1_DONE%"=="1" if "%KB2_DONE%"=="1" (
    echo 所有补丁已安装，可直接安装 WireGuard。
    pause
    exit /b 0
)

:: 安装补丁文件
if "%KB1_DONE%"=="0" if exist "%~dp0KB2921916.msu" (
    echo 安装 KB2921916...
    wusa "%~dp0KB2921916.msu" /quiet /norestart
    set "KB1_DONE=1"
)

if "%KB2_DONE%"=="0" (
    echo 下载 KB3033929...
    bitsadmin /transfer "KB3033929" /download /priority high "https://download.microsoft.com/download/c/8/7/c87ae67e-a228-48fb-8f02-b2a9a1238099/Windows6.1-KB3033929-x64.msu" "%TEMP%\KB3033929.msu" >nul 2>&1
    if exist "%TEMP%\KB3033929.msu" (
        echo 安装 KB3033929...
        wusa "%TEMP%\KB3033929.msu" /quiet /norestart
    )
)

echo.
echo ===== 安装完成 =====
echo 请重启计算机后再安装 WireGuard。
echo.
pause
