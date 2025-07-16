#include <iostream>
#include <string>
#include <sstream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    string input, expected_output, actual_output;
    
    // 读取输入数据（每行一个）
    getline(cin, input);
    getline(cin, expected_output);
    getline(cin, actual_output);
    
    try {
        // 简单的SPJ逻辑：检查实际输出是否包含所有输入数字
        istringstream iss(input);
        vector<int> input_numbers;
        int num;
        while (iss >> num) {
            input_numbers.push_back(num);
        }
        
        istringstream oss(actual_output);
        vector<int> output_numbers;
        while (oss >> num) {
            output_numbers.push_back(num);
        }
        
        // 检查输出是否包含所有输入数字
        bool all_found = true;
        for (int input_num : input_numbers) {
            if (find(output_numbers.begin(), output_numbers.end(), input_num) == output_numbers.end()) {
                all_found = false;
                break;
            }
        }
        
        // 返回JSON格式的结果
        if (all_found) {
            cout << "{\"status\": \"AC\", \"score\": 100, \"message\": \"输出正确\"}" << endl;
        } else {
            cout << "{\"status\": \"WA\", \"score\": 0, \"message\": \"输出错误：缺少输入数字\"}" << endl;
        }
        
    } catch (exception& e) {
        cout << "{\"status\": \"SPJ_ERROR\", \"score\": 0, \"message\": \"SPJ脚本执行错误\"}" << endl;
    }
    
    return 0;
} 