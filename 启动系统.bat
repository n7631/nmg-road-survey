@echo off
chcp 65001 >nul
title 内蒙古公路养护后评价专家咨询系统

echo ============================================================
echo    内蒙古公路养护工程后评价专家咨询系统
echo ============================================================
echo.
echo  正在启动专家端问卷系统 (端口 8501)...
echo.

start "专家端问卷" cmd /k "streamlit run app.py --server.port 8501"

echo  正在启动管理员后台 (端口 8502)...
echo.

start "管理员后台" cmd /k "streamlit run admin.py --server.port 8502"

echo.
echo ============================================================
echo  ✅ 系统已启动！请在浏览器中访问：
echo.
echo     专家端: http://localhost:8501
echo     管理端: http://localhost:8502
echo.
echo  管理员账号: admin
echo  管理员密码: admin123
echo ============================================================
echo.
echo  提示：请将本窗口保持打开，关闭窗口将停止服务。
echo.
pause
