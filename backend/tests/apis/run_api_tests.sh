#!/bin/bash

# 脚本说明：运行API测试
# 用法: ./run_api_tests.sh [测试文件名]

# 设置当前目录
cd "$(dirname "$0")"

# 设置环境变量
export PYTHONPATH=$(pwd)/../../

# 清理Python缓存
echo "清理Python缓存..."
find $PYTHONPATH -type d -name "__pycache__" -exec rm -rf {} +\
    -o -type f -name "*.py[co]" -delete 2>/dev/null || true

# 设置日志文件
LOG_FILE="api_test_log.txt"
echo "测试日志保存在: $LOG_FILE"
> $LOG_FILE

# 判断是否提供了特定测试文件
if [ "$1" ]; then
    TEST_FILE=$1
    echo "运行指定测试文件: $TEST_FILE"
    echo "===== 开始测试 $(date) =====" | tee -a $LOG_FILE
    pytest -xvs $TEST_FILE 2>&1 | tee -a $LOG_FILE
else
    echo "运行所有API测试"
    echo "===== 开始测试 $(date) =====" | tee -a $LOG_FILE
    pytest -xvs test_*.py 2>&1 | tee -a $LOG_FILE
fi

# 检查测试结果
TEST_RESULT=$?
if [ $TEST_RESULT -eq 0 ]; then
    echo "===== 测试通过 $(date) =====" | tee -a $LOG_FILE
else
    echo "===== 测试失败 $(date) =====" | tee -a $LOG_FILE
fi

echo "测试完成，结果代码: $TEST_RESULT"
exit $TEST_RESULT 