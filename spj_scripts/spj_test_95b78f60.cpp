#include <iostream>
#include <string>
#include <sstream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    string input, expected_output, actual_output;
    
    getline(cin, input);
    getline(cin, expected_output);
    getline(cin, actual_output);
    
    try {
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
        
        bool all_found = true;
        for (int input_num : input_numbers) {
            if (find(output_numbers.begin(), output_numbers.end(), input_num) == output_numbers.end()) {
                all_found = false;
                break;
            }
        }
        
        if (all_found) {
            cout << "{\"status\": \"ACCEPTED\", \"score\": 100, \"message\": \"输出正确\"}" << endl;
        } else {
            cout << "{\"status\": \"WRONG_ANSWER\", \"score\": 0, \"message\": \"输出错误\"}" << endl;
        }
        
    } catch (exception& e) {
        cout << "{\"status\": \"SPJ_ERROR\", \"score\": 0, \"message\": \"SPJ脚本执行错误\"}" << endl;
    }
    
    return 0;
}